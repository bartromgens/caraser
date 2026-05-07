# Caraser

Full-stack web application built with Django + DRF (backend) and Angular + Angular Material (frontend).

Upload a street photo and Caraser uses the **Google Gemini** API to produce a car-free version of it, replacing the reclaimed space with trees, benches, greenery and people. Compare the before and after with a drag slider, download the result and share it with others.

## Backend setup

```bash
virtualenv --python=python3.12 env
source env/bin/activate
pip install -r requirements.txt
cp config/settings_local.py.example config/settings_local.py
# Edit config/settings_local.py and set GEMINI_API_KEY (see below)
python manage.py migrate
python manage.py runserver
```

## Frontend setup

```bash
cd client
npm install
npm start
```

The Angular dev server runs on [http://localhost:4200](http://localhost:4200) and proxies `/api` and `/media` requests to Django on port 8000.

## Gemini API key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and create a key.
2. Set it in `config/settings_local.py`:
   ```python
   GEMINI_API_KEY = "your-key-here"
   ```
   Or export it as an environment variable before starting Django:
   ```bash
   export GEMINI_API_KEY="your-key-here"
   ```

The `media/` folder (uploaded and generated images) is git-ignored and created automatically when the first image is processed.

## Related organizations

- [Carfree Cities Alliance](https://www.carfreealliance.org/) — global network advocating for carfree urban living
- [The Lab of Thought](https://thelabofthought.co/) — platform rethinking mobility and public space through research and experimentation
- [Gehl](https://gehl.com/) — urban design consultancy focused on human-scale, people-first cities
- [Strong Towns](https://www.strongtowns.org/) — advocates for financially resilient, walkable communities over car-dependent development
- [ITDP](https://www.itdp.org/) — Institute for Transportation and Development Policy; research and advocacy for sustainable transport globally
- [Streetsblog](https://streetsblog.org/) — media network covering sustainable urban transport and street design

## Production management commands

```bash
docker compose -f docker-compose.prod.yml exec api python manage.py <command>
```