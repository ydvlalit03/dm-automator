from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import verify_password
from database import get_db
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    email = form.get("email", "")
    password = form.get("password", "")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid email or password"}, status_code=401
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
