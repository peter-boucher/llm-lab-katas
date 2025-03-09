# ❤️ LLM LAB – Structured Output, Few-Shot & Query Expansion

## Introduction

In your initial Prompt-to-SQL Pipeline assignment, you built a minimal solution for answering 10 questions on the **Olist** e-commerce dataset. Now, we’ll **refine** that approach by adding:

1. **Structured Output** (using Pydantic in the new **OpenAI Beta** API)
2. **Few-Shot Learning** (to achieve near-perfect SQL accuracy)
3. **Query Expansion** for product categories (user requests in English → database categories in Portuguese)
4. **Chain-of-Thought** considerations (to store or hide reasoning steps)
5. **Debugging & Observability** (including how to handle Chain-of-Thought in logs)

By the end, your solution should still answer the same 10 SQL questions, but with more reliability and clarity. Let’s jump in!

---

## 1. Structured Output with Pydantic (OpenAI Beta)

**What is it?**  
Structured Output means instructing the LLM to produce its answer in a rigid format—commonly JSON—defined by a schema. Using **Pydantic** models, you can automatically enforce that schema on OpenAI’s side, so the model *must* comply.

### Official OpenAI Example (Math Reasoning)

Below is a snippet adapted from the [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs). It demonstrates how the **Chain-of-Thought** style reasoning can be captured in a structured response, with “steps” and a final answer:

```python
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class Step(BaseModel):
    explanation: str
    output: str

class MathReasoning(BaseModel):
    steps: list[Step]
    final_answer: str

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a helpful math tutor. Guide the user through the solution step by step."},
        {"role": "user", "content": "How can I solve 8x + 7 = -23?"}
    ],
    response_format=MathReasoning,
)

math_reasoning = completion.choices[0].message.parsed
print("Steps:", math_reasoning.steps)
print("Final Answer:", math_reasoning.final_answer)
```

**Why is this relevant to your Olist SQL tasks?**
- You can store partial “thinking steps” (similar to chain-of-thought) in a structured format (`steps: list[Step]`).
- You can keep a short “final_answer” or “sql_query” field for the actual result.
- By using Pydantic and `response_format`, the model is constrained to produce exactly those fields.

### Example: SQL Query + Explanation

Here’s a more direct mapping to the Olist scenario. We define a `SQLGeneration` model:

```python
from pydantic import BaseModel, Field
import openai

class SQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description="The final SQL query to answer the user request")

schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "SQLGeneration",
        "strict": True,
        "schema": SQLGeneration.schema()
    }
}

messages = [
    {"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
    {"role": "user", "content": "Which product category has the highest average review score?"}
]

response = openai.ChatCompletion.create(
    model="gpt-4-structure-2025",  # hypothetical future model
    messages=messages,
    response_format=schema
)

parsed_json = response.choices[0].message.content
print(parsed_json)
# => {"steps": ["Join reviews, filter...","Compute average score..."], "sql_query":"SELECT p.product_category_name ..."}
```

This approach yields a small chain-of-thought in `"steps"` plus the final `sql_query`.

> **Note**: In **production** contexts, you often keep chain-of-thought hidden from end-users due to possible inaccuracies or security concerns. But for internal debugging or educational uses, it’s helpful!

---

## 2. Few-Shot Learning

**Recall**: You want accurate SQL for the 10 Olist questions. Provide **2–3** example Q&A pairs to guide the LLM. For example:

```python
few_shot_examples = [
    {"role": "user", "content": "Which seller has delivered the most orders to customers in Rio de Janeiro?"},
    {"role": "assistant", "content": "SELECT seller_id, COUNT(*) AS order_count ..."},
    
    {"role": "user", "content": "What's the average review score for 'beleza_saude' products?"},
    {"role": "assistant", "content": "SELECT AVG(r.review_score)..."},
]

final_prompt = [
    {"role": "system", "content": "You generate strictly valid JSON with steps and sql_query for the Olist DB."}
] + few_shot_examples + [
    {"role": "user", "content": "Which product category has the highest rate of 5-star reviews?"}
]
```

Use that combined message array in your call. The model is then more likely to produce **correct** table names, joins, and logic for the new question.

---

## 3. Query Expansion (English → Portuguese Categories)

**New Requirement**: The user might say “I want to see all electronics.” Meanwhile, your database has `telefonia` or other Portuguese labels. We solve this via a quick step to expand the query:

1. **User** says: “electronics under 100 BRL”
2. **Query Expansion** LLM: “electronics” → “telefonia” (or possibly “eletronicos” if that’s in your schema)
3. **Final SQL** uses `WHERE product_category_name = 'telefonia' AND price < 100`

### Example (English → Portuguese)

```python
import openai

categories = ["beleza_saude","eletronicos","telefonia","utilidades_domesticas"]

prompt = f"""
You are a translator for Olist product categories. 
Valid categories: {', '.join(categories)}
User says: 'electronics'
Return just the single best match in Portuguese from the above list.
"""

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}]
)
portuguese_category = response.choices[0].message.content.strip()

print("Mapped category:", portuguese_category)
# e.g. "telefonia"
```

Then feed `portuguese_category` into your final structured-SQL prompt.

**Note**: You can also do a few-shot approach with synonyms. Show examples like:
- “kitchen stuff” → `utilidades_domesticas`
- “beauty items” → `beleza_saude`

So the model learns the mapping more reliably.

---

## 4. Chain-of-Thought & Debugging

### 4.1 Handling Chain-of-Thought

Including chain-of-thought in your structured output can help internal debugging but may reveal reasoning tokens you don’t want to expose to end-users. Some best practices:

- **Keep steps short**: “step 1: join reviews and order_items,” “step 2: group by category,” etc.
- **Hide in logs**: In production, you might store them in internal logs but present only the final result to the user.
- **Be mindful**: LLMs sometimes produce inaccurate or partial reasoning. Don’t treat chain-of-thought as ground truth.

### 4.2 Debugging & Observability

1. **Logging** – Always log your prompts and raw responses (in dev). If the JSON is invalid, see exactly what was returned.
2. **OpenTelemetry** – You can instrument the **OpenAI** library calls to gather performance metrics (token usage, latency, error codes).
3. **Error Handling** – If the structured output is incomplete or the user request triggers a refusal, catch that and handle gracefully.

#### Example Instrumentation

```python
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import openai

HTTPXClientInstrumentor().instrument()  # Collects telemetry

try:
    response = openai.ChatCompletion.create(
        model="gpt-4-structure-2025",
        messages=[...],
        response_format={...}
    )
except openai.error.OpenAIError as e:
    print("API Error:", e)
```

You’ll see traces in your APM (Application Performance Monitoring) tool for each request, including request/response sizes, durations, etc.

---

## 5. Practical Assignment: Enhance Your Prompt-to-SQL Pipeline

### What to Do

1. **Refactor** your existing code to use Pydantic models and `response_format` from the **OpenAI Beta** API.
2. **Embed 2–3 examples** in the prompt for each tricky question to ensure correctness.
3. **Implement Query Expansion** for product categories. English queries become Portuguese-based category filters.
4. **Optional**: Add a short `steps` chain-of-thought field in your structured output to see how the model reasons, but keep user-facing outputs minimal.
5. **Debug** thoroughly: enable logging, handle malformed or partial outputs, watch out for rate limits, etc.

### Goals

- **Hit 10/10** correctness for the original Olist queries (like “What percentage of orders are delivered before the estimated date?”).
- **Accept** user queries referencing categories in English or synonyms.
- **Produce** valid, parseable JSON (no post-hoc string slicing!).
- **Log & Observe** for performance or weird edge cases.

**Remember**: The best results come from iterating your few-shot examples and adjusting your schema fields to suit your real data needs.

---

## References

1. **Official OpenAI Docs**
    - [Structured Outputs in the API](https://openai.com/index/introducing-structured-outputs-in-the-api/)
    - [OpenAI DevDay 2024 – Example Video](https://youtu.be/kE4BkATIl9c)
    - [Pydantic & Beta Response Formats](https://platform.openai.com/docs/guides/structured-outputs)
2. **Query Expansion**: [Haystack Intro](https://haystack.deepset.ai/blog/query-expansion)
3. **OpenTelemetry**: [Instrumenting HTTPX Calls](https://opentelemetry.io/docs/instrumentation/python/)

---

**That’s it!** By adding structured outputs, few-shot examples, query expansion for Portuguese categories, and chain-of-thought debugging, you’ll bring your Olist pipeline to the next level—**10/10** query accuracy, robust search, and minimal headaches.

**Happy Coding & Good Luck!**  

---
❤️ **LLM LAB – 2025**
