import pytest

@pytest.mark.asyncio
async def test_debug_cookie(client):
    r = await client.get('/auth/register')
    print('GET headers:', r.headers)
    print('GET text snippet:', r.text[:200])
    # valid register flow with unique email
    import uuid
    unique_email = f"debug-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.get('/auth/register')
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    csrf = m.group(1)
    r2 = await client.post('/auth/register', data={'email': unique_email, 'password':'p','confirm_password':'p','csrf_token':csrf}, follow_redirects=False)
    print('POST headers:', r2.headers)
    print('POST status:', r2.status_code)
    print('POST set-cookie:', r2.headers.get('set-cookie'))
    print('POST text:', r2.text[:400])
    # now follow redirect manually if present
    loc = r2.headers.get('location')
    if loc:
        r3 = await client.get(loc)
        text = r3.text
        print('GET after redirect text length:', len(text))
        found = 'Registration successful. Please log in.' in text
        print('Flash present in HTML?', found)
        if not found:
            print('Full HTML (first 2000 chars):', text[:2000])
        print('GET after redirect headers:', r3.headers)
    assert True
