from app import app
c = app.test_client()
rv = c.get('/api/tasks?project=Sample')
print(rv.data.decode('utf-8'))