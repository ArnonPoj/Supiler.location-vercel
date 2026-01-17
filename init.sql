    c.execute('''
        CREATE TABLE IF NOT EXISTS transport_pickup_personal (
            id SERIAL PRIMARY KEY,
            driver_name TEXT NOT NULL,
            phone TEXT,
            note TEXT
        )
    ''')
