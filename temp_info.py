import itertools
with open('accounts/models.py') as f:
    for i,line in enumerate(f,1):
        if 'normalize_whatsapp_number' in line:
            print(i, line.strip())
        if 'USERNAME_FIELD' in line:
            print(i, line.strip())
