import json
import logging
import traceback
from time import perf_counter

from .models import ActivityLog

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    SENSITIVE_KEYWORDS = ('password', 'csrfmiddlewaretoken', 'token', 'secret', 'api_key')
    EXCLUDED_PATHS = ('/static/', '/media/', '/favicon.ico', '/robots.txt')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._audit_start = perf_counter()
        try:
            response = self.get_response(request)
        except Exception as exc:
            logger.exception('Erro ao atender %s %s', request.method, request.path)
            self._log(request, response=None, exception=exc)
            raise
        else:
            self._log(request, response)
            return response

    def _should_log(self, request):
        path = getattr(request, 'path', '')
        return path and not any(path.startswith(prefix) for prefix in self.EXCLUDED_PATHS)

    def _clean_value(self, value):
        text = str(value)
        return text[:2000]

    def _is_sensitive(self, key):
        lowered = key.lower()
        return any(keyword in lowered for keyword in self.SENSITIVE_KEYWORDS)

    def _build_payload(self, request):
        payload = {}
        for query_dict in (request.GET, request.POST):
            if not query_dict:
                continue
            for key, values in query_dict.lists():
                if self._is_sensitive(key):
                    continue
                cleaned = [self._clean_value(value) for value in values]
                payload[key] = cleaned[0] if len(cleaned) == 1 else cleaned
        content_type = request.META.get('CONTENT_TYPE', '')
        if 'json' in content_type.lower():
            try:
                raw = request.body.decode('utf-8')
                if raw:
                    payload['json_body'] = json.loads(raw)
            except json.JSONDecodeError:
                payload['json_body'] = raw[:2000]
            except Exception:
                pass
        return payload or None

    def _get_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _get_duration_ms(self, request):
        start = getattr(request, '_audit_start', None)
        if start is None:
            return None
        return (perf_counter() - start) * 1000

    def _log(self, request, response=None, exception=None):
        if not self._should_log(request):
            return
        status_code = getattr(response, 'status_code', None)
        success = exception is None and (status_code is None or status_code < 400)
        message = ''
        trace = ''
        if exception:
            exception_message = ''.join(traceback.format_exception_only(type(exception), exception)).strip()
            trace = ''.join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
            message = exception_message or message
        elif response is not None:
            message = getattr(response, 'reason_phrase', '')
        if trace:
            message = '\n'.join(filter(None, [message, trace]))
        payload_data = None
        try:
            payload_data = self._build_payload(request)
        except Exception:  # pragma: no cover
            logger.exception('Falha ao montar payload do log de auditoria')
        user_obj = getattr(request, 'user', None)
        if not (user_obj and getattr(user_obj, 'is_authenticated', False)):
            user_obj = None
        resolver = getattr(request, 'resolver_match', None)
        view_name = ''
        if resolver:
            view_name = resolver.view_name or resolver.url_name or ''
        try:
            ActivityLog.objects.create(
                user=user_obj,
                method=request.method,
                path=request.get_full_path(),
                view_name=view_name,
                referer=request.META.get('HTTP_REFERER', '')[:500],
                ip_address=self._get_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                status_code=status_code,
                success=success,
                duration_ms=self._get_duration_ms(request),
                message=message,
                payload=payload_data,
            )
        except Exception:  # pragma: no cover
            logger.exception('Falha ao gravar evento de auditoria')
