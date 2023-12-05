CREATE TABLE users (
    id SERIAL PRIMARY KEY
    , name VARCHAR(45) NOT NULL
    , email VARCHAR(45) NOT NULL
    , status VARCHAR(45) NOT NULL
    , created_at TIMESTAMP DEFAULT NOW()
    , updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sessions (
    id SERIAL PRIMARY KEY
    , id_user INT NOT NULL
    , token VARCHAR(255) NOT NULL
    , status VARCHAR(45) NOT NULL
    , created_at TIMESTAMP DEFAULT NOW()
    , updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY
    , name VARCHAR(45) NOT NULL
    , type VARCHAR(45) NOT NULL
    , created_at TIMESTAMP DEFAULT NOW()
    , created_by INT NOT NULL
    , updated_at TIMESTAMP DEFAULT NOW()
    , updated_by INT NOT NULL
);

CREATE TABLE units (
    id SERIAL PRIMARY KEY
    , name VARCHAR(20) NOT NULL
    , abbreviation VARCHAR(5) NOT NULL
    , base INT NOT NULL
    , created_at TIMESTAMP DEFAULT NOW()
    , created_by INT NOT NULL
    , updated_at TIMESTAMP DEFAULT NOW()
    , updated_by INT NOT NULL
);

CREATE TABLE recipes (
    id SERIAL PRIMARY KEY
    , name VARCHAR(90) NOT NULL
    , description VARCHAR(255)
    , period VARCHAR(45)
    , type VARCHAR(45)
    , presentation VARCHAR(45)
    , created_at TIMESTAMP DEFAULT NOW()
    , created_by INT NOT NULL
    , updated_at TIMESTAMP DEFAULT NOW()
    , updated_by INT NOT NULL
);

CREATE TABLE ingredients (
    id SERIAL PRIMARY KEY
    , name VARCHAR(255) NOT NULL
    , description VARCHAR(255)
    , type VARCHAR(45) NOT NULL
    , created_at TIMESTAMP DEFAULT NOW()
    , created_by INT NOT NULL
    , updated_at TIMESTAMP DEFAULT NOW()
    , updated_by INT NOT NULL
);

CREATE TABLE recipe_ingredients (
    id SERIAL PRIMARY KEY
    , id_recipe INT REFERENCES recipes(id) NOT NULL
    , id_ingredient INT REFERENCES ingredients(id) NOT NULL
    , quantity NUMERIC(10, 2) NOT NULL
    , id_unit INT REFERENCES units(id) NOT NULL
    , created_at TIMESTAMP DEFAULT NOW()
    , created_by INT NOT NULL
    , updated_at TIMESTAMP DEFAULT NOW()
    , updated_by INT NOT NULL
);

-- CREATE TABLE recipe_ingredients_nodes (
--     id serial primary key
--     , id_recipe INT REFERENCES recipes(id) NOT NULL
--     , id_recipe_ingredient INT REFERENCES recipe_ingredients(id) NOT NULL
--     , node_uid varchar(36) not null
--     , node_type varchar(50) not null
--     , node_level integer not null
--     , node_json jsonb not null
--     , created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
--     , created_by INT NOT NULL
--     , updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
--     , updated_by INT NOT NULL
-- );

-- CREATE TABLE recipe_ingredients_edges (
--     id serial primary key
--     , id_recipe INT REFERENCES recipes(id) NOT NULL
--     , id_recipe_ingredient INT REFERENCES recipe_ingredients(id) NOT NULL
--     , source_uid varchar(36) NOT NULL 
--     , target_uid varchar(36) NOT NULL
--     , created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
--     , created_by INT NOT NULL
--     , updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
--     , updated_by INT NOT NULL
-- );

-- CREATE TABLE recipe_files (
--     id serial primary key
--     , id_recipe INT REFERENCES recipes(id) NOT NULL
--     , name varchar(255) NOT NULL
--     , extension varchar(5) NOT NULL
--     , file_bytea BYTEA not null
--     , created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );