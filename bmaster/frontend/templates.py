from fastapi import Request
from fastapi.templating import Jinja2Templates
from bmaster.server import app as front
# from bmaster.frontend import front

templates = Jinja2Templates(directory="templates")

def get_fake_schedule():
    return {
        "schedule": [
            {
                "time": "08:29",
                "filePath": "sounds/example.wav",
                "type": "warn"
            },
            {
                "time": "08:30",
                "filePath": "sounds/example.wav",
                "type": "start"
            },
            {
                "time": "09:15",
                "filePath": "sounds/example.wav",
                "type": "end"
            }
        ],
        "settings": {
            "enabled_anouncements": False,
            "use_single_sound": True,
            "enabled_holidayMode": False,
            "default_bell_duration": "7",
            "time_to_warn": "1"
        }
    }

def transform_schedule_for_flask():
    return [{
        "start_time": "08:30",
        "end_time": "09:15",
        "start_sound_path": "sounds/example.wav",
        "end_sound_path": "sounds/example.wav"
    }]

def get_fake_sounds():
    return [
        {'name': 'Example Sound', 'path': 'sounds/example.wav'}
    ]

@front.get("/")
@front.get("/index")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "schedule": transform_schedule_for_flask(),
        "sounds_specs": get_fake_sounds()
    })

@front.get("/announcements")
async def announcements(request: Request):
    return templates.TemplateResponse("announcements.html", {
        "request": request,
        "sounds_specs": get_fake_sounds()
    })

@front.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@front.get("/register")
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@front.get("/profile")
async def profile(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@front.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": get_fake_schedule()["settings"]
    })

@front.get("/sounds")
async def sounds(request: Request):
    return templates.TemplateResponse("sounds.html", {
        "request": request,
        "specs_list": get_fake_sounds()
    })