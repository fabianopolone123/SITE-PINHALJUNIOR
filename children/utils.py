import datetime

from accounts.models import User
from children.models import Child, ChildFace, ChildHealth, GuardianChild


CLASS_MAP = {
    6: 'Abelhinhas Laboriosas',
    7: 'Luminares',
    8: 'Edificadores',
    9: 'Mãos Ajudadoras',
}


def _calculate_age(birth_date: datetime.date) -> int:
    today = datetime.date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def determine_class_group(birth_date: datetime.date) -> str:
    return CLASS_MAP.get(_calculate_age(birth_date), '')


def collect_children_payload(post_data, files=None):
    errors = []
    payloads = []
    files = files or {}
    child_names = post_data.getlist('child_name')
    child_lastnames = post_data.getlist('child_last')
    child_births = post_data.getlist('child_birth')
    child_genders = post_data.getlist('child_gender')
    child_cpfs = post_data.getlist('child_cpf')
    child_birth_certs = post_data.getlist('child_birth_certificate')
    child_father_names = post_data.getlist('child_father_name')
    child_father_cpfs = post_data.getlist('child_father_cpf')
    child_father_phones = post_data.getlist('child_father_phone')
    child_father_absent = post_data.getlist('child_father_absent')
    child_mother_names = post_data.getlist('child_mother_name')
    child_mother_cpfs = post_data.getlist('child_mother_cpf')
    child_mother_phones = post_data.getlist('child_mother_phone')
    child_mother_absent = post_data.getlist('child_mother_absent')
    child_allergies = post_data.getlist('child_allergies')
    child_meds = post_data.getlist('child_meds')
    child_restr = post_data.getlist('child_restr')
    child_obs = post_data.getlist('child_obs')
    child_emerg = post_data.getlist('child_emerg')
    child_emerg_phone = post_data.getlist('child_emerg_phone')
    child_plan = post_data.getlist('child_plan')
    child_auth_activity = post_data.getlist('child_auth_activity')
    child_auth_medical = post_data.getlist('child_auth_medical')
    child_auth_rules = post_data.getlist('child_auth_rules')

    if not child_names:
        errors.append('Adicione pelo menos um aventureiro.')
    for idx, name in enumerate(child_names):
        first = (name or '').strip()
        last = (child_lastnames[idx] or '').strip() if idx < len(child_lastnames) else ''
        full_name = f'{first} {last}'.strip()
        birth_raw = (child_births[idx] or '') if idx < len(child_births) else ''
        gender = (child_genders[idx] or '').strip()
        cpf_child = (child_cpfs[idx] or '').strip() if idx < len(child_cpfs) else ''
        if not first or not birth_raw:
            errors.append('Cada aventureiro precisa de nome e data de nascimento.')
            continue
        try:
            birth_date = datetime.date.fromisoformat(birth_raw)
        except ValueError:
            errors.append(f'Data inválida para {full_name or "o aventureiro"}')
            continue
        auth_activity = str(idx) in child_auth_activity or 'on' in child_auth_activity
        auth_medical = str(idx) in child_auth_medical or 'on' in child_auth_medical
        auth_rules = str(idx) in child_auth_rules or 'on' in child_auth_rules
        if not (auth_activity and auth_medical and auth_rules):
            errors.append(f'Autorizações obrigatórias não marcadas para {full_name}.')
        face_file = files.get(f'child_photo_{idx}')
        payloads.append(
            {
                'name': full_name,
                'birth_date': birth_date,
                'gender': gender,
                'cpf': cpf_child,
                'birth_certificate': (child_birth_certs[idx] or '') if idx < len(child_birth_certs) else '',
                'father_name': (child_father_names[idx] or '') if idx < len(child_father_names) else '',
                'father_cpf': (child_father_cpfs[idx] or '') if idx < len(child_father_cpfs) else '',
                'father_phone': (child_father_phones[idx] or '') if idx < len(child_father_phones) else '',
                'father_absent': str(idx) in child_father_absent,
                'mother_name': (child_mother_names[idx] or '') if idx < len(child_mother_names) else '',
                'mother_cpf': (child_mother_cpfs[idx] or '') if idx < len(child_mother_cpfs) else '',
                'mother_phone': (child_mother_phones[idx] or '') if idx < len(child_mother_phones) else '',
                'mother_absent': str(idx) in child_mother_absent,
                'allergies': (child_allergies[idx] or '') if idx < len(child_allergies) else '',
                'meds': (child_meds[idx] or '') if idx < len(child_meds) else '',
                'restr': (child_restr[idx] or '') if idx < len(child_restr) else '',
                'obs': (child_obs[idx] or '') if idx < len(child_obs) else '',
                'emerg': (child_emerg[idx] or '') if idx < len(child_emerg) else '',
                'emerg_phone': (child_emerg_phone[idx] or '') if idx < len(child_emerg_phone) else '',
                'plan': (child_plan[idx] or '') if idx < len(child_plan) else '',
                'auth_activity': auth_activity,
                'auth_medical': auth_medical,
                'auth_rules': auth_rules,
                'face_file': face_file,
            }
        )
    return payloads, errors


def create_child_with_health(guardian_user, payload):
    child = Child.objects.create(
        name=payload['name'],
        birth_date=payload['birth_date'],
        gender=payload['gender'],
        cpf=payload['cpf'],
        active=True,
        class_group=determine_class_group(payload['birth_date']),
        birth_certificate_number=payload.get('birth_certificate', ''),
        father_name=payload.get('father_name', '') if not payload.get('father_absent') else '',
        father_cpf=payload.get('father_cpf', '') if not payload.get('father_absent') else '',
        father_phone=payload.get('father_phone', '') if not payload.get('father_absent') else '',
        father_absent=payload.get('father_absent', False),
        mother_name=payload.get('mother_name', '') if not payload.get('mother_absent') else '',
        mother_cpf=payload.get('mother_cpf', '') if not payload.get('mother_absent') else '',
        mother_phone=payload.get('mother_phone', '') if not payload.get('mother_absent') else '',
        mother_absent=payload.get('mother_absent', False),
    )
    GuardianChild.objects.create(
        guardian_user=guardian_user,
        child=child,
        relationship='Responsável',
    )
    ChildHealth.objects.create(
        child=child,
        allergies=payload['allergies'],
        medications=payload['meds'],
        restrictions=payload['restr'],
        observations=payload['obs'],
        emergency_contact=payload['emerg'],
        emergency_phone=payload['emerg_phone'],
        health_plan=payload['plan'],
        auth_activity=payload['auth_activity'],
        auth_medical=payload['auth_medical'],
        auth_rules=payload['auth_rules'],
    )
    face_file = payload.get('face_file')
    if face_file:
        ChildFace.objects.create(child=child, image=face_file)
    return child
