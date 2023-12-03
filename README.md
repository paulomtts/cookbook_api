# cookbook_api 🍔
This is the API for the Cookbook app! The goal is to be a simple demonstration of SQLAlchemy, SQLModel & Pandas usage in building easy to read interactions with a database. Here are a few features:

- Nested, bulk & returning operations
- Returnings allow for OOP during chained operations
- Pandas usage allows for easy data manipulation
- Allows for complex queries (see queries.py and its use in routes.py's /custom/submit_recipe)
- Writing complex chained operations is a piece of 🍰
- You don't need to worry about parsing to JSON while writing custom routes, APIOutput schema will do it for you

To achieve this, simply write a callback like the one below:
```
@db.catching(messages=SuccessMessages('Submission succesful.'))
def submit_data(form_data, upsert_data):
    form_object = db.upsert(Recipes, [form_data], single=True)
    upserted_rows = db.upsert(RecipeIngredients, [{**row, 'id_recipe': form_object.id} for row in upsert_data])

    return upserted_rows

content, status_code, client_message = submit_data(form_data, upsert_data)
```

This project is usable out of the box. Don't forget to setup your enviroment variables! 🚀

## Comming up
- [ ] Google OAuth
- [ ] Image files upload route
- [ ] FastAPI schemas
