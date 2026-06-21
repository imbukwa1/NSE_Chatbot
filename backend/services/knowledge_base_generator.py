"""Generate beginner-friendly NSE knowledge-base entries.

The generated JSON is deterministic so it can be committed and reused by the
chatbot without depending on external AI calls or test data.
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "nse_kb_200.json"

CATEGORIES = {
    "Basic Concepts": [
        (
            "What is a share?",
            "A share represents ownership in a company. Buying shares makes you a partial owner of that company.",
        ),
        (
            "What is a dividend?",
            "A dividend is a portion of a company's profits paid to shareholders as a reward for investing.",
        ),
        (
            "What is a stock exchange?",
            "A stock exchange is a regulated marketplace where shares and securities are bought and sold.",
        ),
        (
            "What is the NSE?",
            "The Nairobi Securities Exchange (NSE) is Kenya's main stock market where securities are traded.",
        ),
        (
            "What is market capitalization?",
            "Market capitalization is the total value of a company's shares in the stock market.",
        ),
        (
            "What is a portfolio?",
            "A portfolio is a collection of financial investments such as shares, bonds, and assets.",
        ),
    ],
    "Trading Concepts": [
        (
            "What is buying and selling of shares?",
            "Buying shares means acquiring ownership in a company, while selling means transferring ownership to another investor.",
        ),
        (
            "What is a bull market?",
            "A bull market is a period of rising stock prices and strong investor confidence.",
        ),
        (
            "What is a bear market?",
            "A bear market is a period of falling stock prices and low investor confidence.",
        ),
        (
            "What is liquidity?",
            "Liquidity refers to how quickly an asset can be bought or sold without affecting its price.",
        ),
        (
            "What is a market order?",
            "A market order executes a trade immediately at the current market price.",
        ),
        (
            "What is a limit order?",
            "A limit order executes a trade only at a specified price or better.",
        ),
    ],
    "NSE-specific Information": [
        (
            "What companies are listed on NSE?",
            "The NSE lists companies like Safaricom, Equity Group, KCB Group, and many others.",
        ),
        (
            "What is NSE 20 Share Index?",
            "It is an index that tracks the performance of 20 top companies on the NSE.",
        ),
        (
            "What are NSE trading hours?",
            "The NSE operates Monday to Friday from 9:30 AM to 3:00 PM excluding public holidays.",
        ),
        (
            "What is settlement in NSE?",
            "Settlement is the process where shares and money are exchanged after a trade is completed.",
        ),
        (
            "What is the role of NSE?",
            "The NSE facilitates buying and selling of securities in Kenya.",
        ),
        (
            "What is a stock index?",
            "A stock index measures the performance of selected groups of stocks in the market.",
        ),
    ],
    "Investment Basics": [
        (
            "What is risk vs return?",
            "Higher investment returns usually come with higher levels of risk.",
        ),
        (
            "What is diversification?",
            "Diversification is spreading investments across different assets to reduce risk.",
        ),
        (
            "What is compound interest?",
            "Compound interest is interest earned on both initial capital and accumulated interest.",
        ),
        (
            "What is capital gain?",
            "Capital gain is the profit made when selling an asset at a higher price than purchase price.",
        ),
        (
            "What is long-term investing?",
            "Long-term investing involves holding assets for an extended period to grow wealth.",
        ),
        (
            "What is inflation?",
            "Inflation is the rise in prices of goods and services over time, reducing purchasing power.",
        ),
    ],
}

QUESTION_TEMPLATES = (
    "{base}",
    "Explain {subject}",
    "Define {subject}",
    "What does {subject} mean?",
    "Why is {subject} important?",
    "How should beginners understand {subject}?",
    "Give a beginner explanation of {subject}",
    "What should NSE investors know about {subject}?",
    "How does {subject} work?",
)


def _subject_from_question(question: str) -> str:
    subject = question.strip().rstrip("?")
    for prefix in ("What is ", "What are ", "What companies are "):
        if subject.startswith(prefix):
            subject = subject[len(prefix):]
            break
    return subject[0].lower() + subject[1:] if subject else question


def _keywords(question: str, subject: str, category: str) -> list[str]:
    words = {
        category.lower(),
        subject.lower(),
        question.lower().rstrip("?"),
    }
    for token in subject.replace("-", " ").split():
        if len(token) > 2:
            words.add(token.lower())
    return sorted(words)


def generate_entries(entries_per_category: int = 50) -> list[dict]:
    dataset = []
    entry_id = 1

    for category, items in CATEGORIES.items():
        expanded = []
        for base_question, base_answer in items:
            subject = _subject_from_question(base_question)
            for template in QUESTION_TEMPLATES:
                question = template.format(base=base_question, subject=subject)
                answer = base_answer
                if question != base_question:
                    answer = (
                        f"{base_answer} This is important for beginner investors to understand."
                    )
                expanded.append((question, answer, subject))

        for question, answer, subject in expanded[:entries_per_category]:
            dataset.append(
                {
                    "id": f"{category[:4].lower()}_{entry_id}",
                    "category": category,
                    "question": question,
                    "answer": answer,
                    "tags": [category.lower().replace(" ", "_")],
                    "keywords": _keywords(question, subject, category),
                    "difficulty": "beginner",
                }
            )
            entry_id += 1

    return dataset


def write_entries(path: Path = DATA_PATH) -> list[dict]:
    data = generate_entries()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


if __name__ == "__main__":
    entries = write_entries()
    print(f"Generated {len(entries)} entries successfully at {DATA_PATH}")
