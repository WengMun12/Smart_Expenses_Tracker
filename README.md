# Smart Expense Tracker

A mobile app for tracking personal expenses, with AI-powered entry. Type something or scan a receipt photo, the app fills in the amount, description and category for you.

## Screenshots
| Login | Sign up | Expenses | AI Auto-fill | Receipt Scan |
|---|---|---|---|---|
| <img width="390" height="842" alt="image" src="https://github.com/user-attachments/assets/ddcde45f-809d-48d2-920a-6a242e9647fa" /> | <img width="385" height="840" alt="image" src="https://github.com/user-attachments/assets/3de4d5be-2194-4bb7-befc-486d9d2d91eb" /> | <img width="386" height="842" alt="image" src="https://github.com/user-attachments/assets/7dd3b6c9-ad3d-43b0-b0f5-1df318ee6b3e" /> | <img width="393" height="847" alt="image" src="https://github.com/user-attachments/assets/f6427289-c4aa-452e-9775-062d3ed00e5f" /> | <img width="387" height="843" alt="image" src="https://github.com/user-attachments/assets/3e4ec4ec-2b8d-4ec7-8600-cf30c7deecfd" /> |

## Features 
- User sign up ang log in (JWT Authentication, bycrpt password hashing)
- Add, view and delete expenses
- Category dropdown loaded from database
- AI auto-fill: natural languages input converts to amount, description and category
- Receipt Scanning: tale a photo or pick one from gallery and the app extracts the total, store name and category
- Review before saving: AI results fill the form and user confirm or edits

## Tech Stack
| Layer | Technology |
|---|---|
| Mobile app | Flutter, Dart |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | MySQL |
| Auth | JWT, bycrpt |
| AI | Google Gemini API (text and image input) |

## Architecture
Flutter app -> FastAPI REST API -> MySQL
                       |
                       -> Gemini API
...                       
(The app never talks to the database or the AI directly. The backend holds all secrets and check user's token on every request and retries with a fallback model if the AI service is busy.)

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
| POST | /ai/receipt | Convert a receipt image into expense details |

## Database
Three tables: 'users', 'category', 'expenses'

## Future Improvements
- Edit expenses
- Monthly totals and charts
- Persist login with secure storage
