CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(45) NOT NULL,
    type VARCHAR(45) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) NOT NULL,
    abbreviation VARCHAR(5) NOT NULL,
    base INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(90) NOT NULL,
    description VARCHAR(255),
    period VARCHAR(45),
    type VARCHAR(45),
    presentation VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    type VARCHAR(45) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE recipe_ingredients (
    id SERIAL PRIMARY KEY,
    id_recipe INT REFERENCES recipes(id) NOT NULL,
    id_ingredient INT REFERENCES ingredients(id) NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL,
    id_unit INT REFERENCES units(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
