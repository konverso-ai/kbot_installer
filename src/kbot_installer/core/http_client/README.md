# HTTP Client Package

Un package Python pour interagir avec des APIs de manière dynamique et fluide, sans contraintes de schéma prédéfini.

## 🚀 Fonctionnalités

- **Construction dynamique des chemins** : `client.api.v1.repo.anything`
- **Paramètres de chemin** : `client.api.v1.repo(id=123)`
- **Paramètres de requête** : `client.api.v1.repo().query(sort="name")`
- **Méthodes HTTP complètes** : GET, POST, PUT, DELETE, PATCH
- **Authentification flexible** : Basic, Bearer, API Key
- **Interface fluide** : Chaînage naturel des méthodes
- **Support async/await** : Compatible avec les applications asynchrones

## 📦 Installation

```bash
# Le package est déjà inclus dans le projet
# Aucune installation supplémentaire nécessaire
```

## 🎯 Utilisation de Base

### Initialisation

```python
from http_client import ApiClient, BasicAuth, BearerAuth, ApiKeyAuth

# Client sans authentification
client = ApiClient("https://api.example.com")

# Client avec authentification Basic
client = ApiClient("https://api.example.com", auth=BasicAuth("user", "pass"))

# Client avec authentification Bearer
client = ApiClient("https://api.example.com", auth=BearerAuth("token123"))

# Client avec clé API
client = ApiClient("https://api.example.com", auth=ApiKeyAuth("key123", "X-API-Key"))
```

### Construction Dynamique des Chemins

```python
# Construction simple
path = client.api.v1.users
# Construit: /api/v1/users

# Avec paramètres de chemin
path = client.api.v1.users(id=123)
# Construit: /api/v1/users/{id} -> /api/v1/users/123

# Chaînage complexe
path = client.api.v1.repo(id=123).files(file_id=456).comments(comment_id=789)
# Construit: /api/v1/repo/123/files/456/comments/789
```

### Paramètres de Requête

```python
# Paramètres de requête simples
query_path = client.api.v1.users().query(sort="name", limit=10)
# Construit: /api/v1/users?sort=name&limit=10

# Chaînage avec paramètres de chemin et de requête
query_path = client.api.v1.users(id=123).posts().query(sort="date", limit=10)
# Construit: /api/v1/users/123/posts?sort=date&limit=10
```

### Exécution des Requêtes

```python
# Requête GET
response = await client.api.v1.users.get()

# Requête GET avec paramètres
response = await client.api.v1.users(id=123).get()

# Requête GET avec paramètres de requête
response = await client.api.v1.users().query(sort="name").get()

# Requête POST avec données JSON
response = await client.api.v1.users.post(json_data={"name": "John", "email": "john@example.com"})

# Requête PUT avec données
response = await client.api.v1.users(id=123).put(json_data={"name": "Jane"})

# Requête DELETE
response = await client.api.v1.users(id=123).delete()

# Requête PATCH
response = await client.api.v1.users(id=123).patch(json_data={"name": "Updated"})
```

## 🔧 Exemples Avancés

### GitHub API

```python
client = ApiClient("https://api.github.com")

# Obtenir les informations d'un utilisateur
response = await client.users.octocat.get()

# Obtenir les repositories avec paramètres
response = await client.users.octocat.repos().query(
    sort="updated",
    per_page=5,
    type="public"
).get()

# Obtenir les issues d'un repository
response = await client.repos.octocat.Hello_World.issues.get()
```

### API REST Complexe

```python
client = ApiClient("https://api.example.com", auth=BearerAuth("token"))

# Construction complexe avec paramètres
response = await client.api.v2.users(user_id=123).posts(post_id=456).comments().query(
    sort="date",
    limit=20,
    offset=0
).get()

# Création de ressource
new_post = {
    "title": "Mon nouveau post",
    "content": "Contenu du post",
    "author_id": 123
}
response = await client.api.v2.posts.post(json_data=new_post)
```

### Gestion des Erreurs

```python
from http_client.exceptions import HttpClientError, TimeoutError, AuthenticationError

try:
    response = await client.api.v1.users.get()
    print(f"Status: {response.status_code}")
    data = response.json()
except TimeoutError:
    print("La requête a expiré")
except AuthenticationError:
    print("Erreur d'authentification")
except HttpClientError as e:
    print(f"Erreur HTTP: {e}")
```

## 🏗️ Architecture

### Classes Principales

- **`ApiClient`** : Client principal pour les requêtes HTTP
- **`ApiPath`** : Construction dynamique des chemins
- **`QueryPath`** : Gestion des paramètres de requête
- **`BasicAuth`** : Authentification Basic
- **`BearerAuth`** : Authentification Bearer Token
- **`ApiKeyAuth`** : Authentification par clé API

### Types d'Authentification

```python
# Basic Authentication
auth = BasicAuth("username", "password")

# Bearer Token
auth = BearerAuth("your-token-here")

# API Key (dans les headers)
auth = ApiKeyAuth("your-api-key", "X-API-Key")

# API Key (dans les paramètres de requête)
auth = ApiKeyAuth("your-api-key", "api_key", in_query=True)
```

## 🧪 Tests

```bash
# Exécuter les tests
uv run python -B test_http_client.py

# Exécuter les exemples
uv run python -B http_client_example.py
```

## 📝 Notes de Développement

- Compatible Python 3.8+
- Utilise `httpx` comme client HTTP de base
- Support complet async/await
- Type hints complets
- Gestion d'erreurs robuste
- Interface fluide et intuitive

## 🔮 Roadmap

- [ ] Support des schémas OpenAPI/Swagger
- [ ] Cache des réponses
- [ ] Retry automatique
- [ ] Rate limiting
- [ ] Middleware support
- [ ] Logging des requêtes
- [ ] Validation des paramètres

## 🤝 Contribution

Ce package fait partie du projet `kbot_installer`. Pour contribuer :

1. Suivez les conventions de code du projet
2. Ajoutez des tests pour les nouvelles fonctionnalités
3. Documentez les changements
4. Respectez les règles de linting (ruff)

## 📄 Licence

Ce package fait partie du projet `kbot_installer` et suit la même licence.
