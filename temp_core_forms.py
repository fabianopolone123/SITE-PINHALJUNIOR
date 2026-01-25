with open('core/forms.py') as f:
    for i,line in enumerate(f,1):
        if 'AdventureLoginForm' in line or 'clean_whatsapp_number' in line:
            print(i, line.strip())
        if 'normalize_whatsapp_number' in line:
            print(i, line.strip())
