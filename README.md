# Smart Expense Tracker

A mobile app for tracking personal expenses, with AI-powered auto-fill. Type something and the app fills in the amount, description and category for you.

## Screenshots
| Login | Expenses | Add with AI |
|---|---|---|
| <img width="367" height="805" alt="image" src="https://github.com/user-attachments/assets/b0aaf613-3304-471f-8f81-9e46893cb6c5" /> | <img width="381" height="795" alt="image" src="https://github.com/user-attachments/assets/2e80f7d7-3371-48f2-bcfb-a6b1a3a1800e" /> | <img width="378" height="796" alt="image" src="https://github.com/user-attachments/assets/6fdc7d00-327d-4b03-8629-c1f20fb34db5" /> |

## Features 
- User sign up ang log in (JWT Authentication, bycrpt password hashing)
- Add, view and delete expenses
- Category dropdown loaded from database
- AI auto-fill: natural languages input converts to amount, description and category using Gemini API

## Tech Stack
| Layer | Technology |
|---|---|
| Mobile app | Flutter, Dart |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | MySQL |
| Auth | JWT, bycrpt |
| AI | Google Gemini API |

## Architecture
Flutter app -> FastAPI REST API -> MySQL
                       |
                       -> Gemini API
(The app never talks to the database or the AI directly. The backend holds all secrets and check user's token on every request.)

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | /signup | Creates an account |
| POST | /login | Log in, returns a JWT |
| GET | /expenses | List the user's expenses |
| POST | /expenses | Add an expense |
| PUT | /expenses/{id} | Update an expense |
| DELETE | /expenses/{id} | Delete an expense |
| GET | /category | List categories |
| POST | /ai/categorize | Parse text into expense details |

## Database
Three tables: 'users', 'category', 'expenses'

## Future Improvements
- Sign-up screen in the app
- Edit expenses
- Monthly totals and charts
- Persist login with secure storage
