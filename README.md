# NSE Chatbot

An intelligent chatbot project designed to provide insights and data visualizations for the National Stock Exchange (NSE).

## 🚀 Features

- **Interactive Chat Interface**: Real-time communication for querying stock data.
- **Data Visualization**: Integrated with **Recharts** for high-quality, responsive stock market charts.
- **Efficient Storage**: Utilizes **Keyv** for consistent key-value storage across multiple backends.
- **Robust Architecture**: Implements `@humanwhocodes/retry` for resilient API interactions and `@humanfs` for standardized file system bindings.

## 🛠️ Tech Stack

- **Frontend**: React / Next.js
- **Charts**: Recharts
- **Storage**: Keyv
- **Utilities**: @humanfs, @humanwhocodes/retry

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd NSE_Chatbot
   ```

2. **Install dependencies:**
   ```bash
   # Install root dependencies (if any)
   npm install

   # Install frontend dependencies
   cd frontend
   npm install
   ```

## 🚦 Running the Project

Navigate to the `frontend` directory and start the development server:
```bash
npm run dev
```

## 📄 License

This project is licensed under the MIT License.