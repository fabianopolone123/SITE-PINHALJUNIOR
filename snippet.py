with open('templates/finance/pix_payment.html', 'rb') as f:
    data = f.read()
search = b"mp_payment_error"
idx = data.index(search)
print(data[idx-60:idx+200])
