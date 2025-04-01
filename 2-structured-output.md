# ❤️ LLM LAB – Structured Output, Few-Shot & Query Expansion

## Introduction

In the initial Prompt-to-SQL Pipeline assignment, you built a minimal solution to answer ten questions on the **Olist** e-commerce dataset. Now it’s time to **refine** that approach by adding some powerful techniques:

1. **Structured Output** (using Pydantic with the new **OpenAI Beta** API)  
2. **Few-Shot Learning** (to achieve near-perfect SQL accuracy)
3. **Query Expansion** for product categories (user requests in English → database categories in Portuguese)
4. **Chain-of-Thought** enhancements (to capture or hide reasoning steps)  
5. **Debugging & Observability** improvements (including how to handle chain-of-thought in logs)  

By the end, your improved pipeline will still answer the same 10 SQL questions as before, but with greater reliability and clarity. Let’s jump in!

---

## Structured Output with Pydantic (OpenAI Beta)

**What is it?**  
Structured output involves instructing the LLM to produce its answer in a strict format (commonly JSON) defined by a schema. Using **Pydantic** models with OpenAI’s Beta API, you can enforce that schema on OpenAI’s side so the model *must* comply.

### Official OpenAI Example (Math Reasoning)

Below is a snippet adapted from the [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs). It demonstrates how **chain-of-thought** style reasoning can be captured in a structured response with a list of “steps” and a final answer:

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
- You can capture partial “thinking steps” (similar to a chain-of-thought) in a structured field like `steps` (e.g. `steps: list[Step]`).  
- You can keep a short `final_answer` or `sql_query` field for the actual result.  
- By using Pydantic with `response_format`, the model is constrained to produce exactly those fields (nothing more, nothing less).

### Example: SQL Query + Explanation

Here’s a more direct mapping to the Olist scenario. We define a `SQLGeneration` model for our responses:

```python
from pydantic import BaseModel, Field
import openai

class SQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description="The final SQL query to answer the user request")

client = OpenAI()

messages = [
    {"role": "system", "content": "You are an expert in Olist's database. Provide 1-3 short reasoning steps, then a final SQL query."},
    {"role": "user", "content": "Which product category has the highest average review score?"}
]

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=messages,
    response_format=SQLGeneration
)

parsed_json = response.choices[0].message.content
print(parsed_json)
# => {"steps": ["Join reviews, filter...","Compute average score..."], "sql_query":"SELECT p.product_category_name ..."}
```
> [!TIP]
> Use `Field(..., description="Extra instruction for this field only")` to add a prompt specific to each field. These field-specific instructions can even replace parts of your system prompt. Funny enough, field descriptions **do not** count against token usage, so this can be a clever way to save tokens. (Be aware that compiling a large Pydantic schema for the first time can be slow—sometimes minutes for very big models—but the compiled model is cached globally after that.)

This approach yields a short chain-of-thought in the `"steps"` field plus the final query in `"sql_query"`.

> [!CAUTION]
> In **production**, you’ll usually hide the chain-of-thought from end users to avoid exposing inaccurate or sensitive reasoning. For internal debugging or educational purposes, however, it’s extremely helpful to include it.

---

## Few-Shot Learning

**What is it?**  
Few-shot learning is a prompting technique where we provide the LLM with 2–3 example question-and-answer pairs to guide its responses. These examples help the model understand the expected format, style, and logic for generating SQL queries tailored to your database schema.

**Why use it?**  
By showing concrete examples of correct SQL queries for your database, you greatly reduce schema hallucinations. You also teach the model how to handle specific joins and table relationships, and you demonstrate the preferred SQL style and query patterns.

> [!TIP]
> The quality of your few-shot examples directly affects the model’s performance. Always use expert-validated, well-tested SQL examples to avoid confusing the model or degrading the prompt’s effectiveness.

### Multiple Ways to Incorporate Few-Shot Examples

There are several effective approaches to implementing few-shot learning in your prompt-to-SQL pipeline:

#### Mimic Assistant Answers to User Queries

One simple method is to include example Q&A pairs directly in the chat history before the user’s actual question. For instance:

```python
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI()

# Define our structured output format
class SQLGeneration(BaseModel):
    reasoning: list[str] = Field(..., description="Short reasoning steps explaining the approach")
    sql_query: str = Field(..., description="The final SQL query (PostgreSQL syntax)")

user_question = "Which product category has the highest rate of 5-star reviews?"
    
# Create a conversation with few-shot examples
messages = [
    {"role": "system", "content": "You are a SQL expert developer. Generate SQL queries for the Olist e-commerce database. Provide only the SQL query with no explanation."},
    {"role": "user", "content": "Which seller has delivered the most orders to customers in Rio de Janeiro?"}, 
    {"role": "assistant", "content": "SELECT s.seller_id, COUNT(*) AS order_count FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN sellers s ON o.seller_id = s.seller_id WHERE c.customer_city = 'rio de janeiro' AND o.order_status = 'delivered' GROUP BY s.seller_id ORDER BY order_count DESC LIMIT 1;"},
    {"role": "user", "content": "What's the average review score for 'beleza_saude' products?"},
    {"role": "assistant", "content": "SELECT AVG(r.review_score) AS avg_score FROM order_reviews r JOIN order_items oi ON r.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'beleza_saude';"},
    {"role": "user", "content": user_question}
]

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=messages,
    response_format=SQLGeneration
)

result = response.choices[0].message.parsed
print("Reasoning steps:")
for idx, step in enumerate(result.reasoning, 1):
    print(f"{idx}. {step}")
print("\nSQL Query:")
print(result.sql_query)
```

> [!TIP]
> In this approach, we primed the model with a "fake" chat history of examples. The LLM infers the pattern from these examples and uses it to generate the next answer in a similar style.

#### Chat History and Iterative Feedback Refinement

Another, more advanced technique is to combine the few-shot chat history with an automated feedback loop to create a self-improving system:

```python
from pydantic import BaseModel, Field
from openai import OpenAI
import json

client = OpenAI()

# Define structured output format for SQL generation
class SQLGeneration(BaseModel):
    reasoning: list[str] = Field(..., description="Short reasoning steps explaining the approach")
    sql_query: str = Field(..., description="The final SQL query (PostgreSQL syntax)")

# Function to evaluate SQL quality using an LLM
def evaluate_sql(generated_sql, correct_sql, query_description):
    """Evaluate the generated SQL against the correct SQL using an LLM"""
    eval_prompt = f"""
    As a SQL expert, evaluate the generated SQL query against the correct SQL query.
    
    Query task: {query_description}
    
    Generated SQL: {generated_sql}
    
    Correct SQL: {correct_sql}
    
    Provide a JSON response with the following fields:
    - "is_correct": boolean (true if functionally equivalent, false otherwise)
    - "errors": list of string errors if any (empty list if correct)
    - "correction": string with corrected SQL if needed (empty string if correct)
    - "explanation": string explaining what was wrong and how it was fixed
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a SQL expert evaluator."},
                 {"role": "user", "content": eval_prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result

# Build a growing conversation with automatic feedback
def build_conversation_with_feedback(test_queries, correct_sql_map, system_prompt):
    """Build a conversation history with automatic feedback for improvement"""
    conversation = [{"role": "system", "content": system_prompt}]
    for query_desc, user_query in test_queries.items():
        # Add the user question
        conversation.append({"role": "user", "content": user_query})
        # Get model response (SQLGeneration parsed output)
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=conversation,
            response_format=SQLGeneration
        )
        
        generated_sql = response.choices[0].message.parsed.sql_query
        correct_sql = correct_sql_map[query_desc]
        # Evaluate the SQL correctness
        evaluation = evaluate_sql(generated_sql, correct_sql, query_desc)
        # Add the assistant's SQL answer to the conversation history
        conversation.append({"role": "assistant", "content": generated_sql})
        # If SQL was incorrect, provide feedback and the correct answer
        if not evaluation["is_correct"]:
            feedback = f"""
            Your SQL query has some issues:
            {evaluation["explanation"]}
            
            Corrected SQL:
            {evaluation["correction"]}
            """
            
            conversation.append({"role": "user", "content": feedback})
            conversation.append({"role": "assistant", "content": evaluation["correction"]})
    
    return conversation
```

> [!NOTE]
> This automated feedback loop is especially useful in production. It enables continuous improvement based on evaluation data **without** requiring you to manually tweak prompts for each new error.

## Query Expansion

**What is it?**  
Query expansion is a technique that enhances the original user query with additional related terms, synonyms, or contextual information. This bridges the gap between how users naturally express their needs and how data is structured in your database, improving search coverage.

**Key Use Cases:**  
- **Cross-language mapping** – e.g. mapping English user terms to the equivalent Portuguese terms in the database.  
- **Synonym expansion** – include common synonyms or alternate terms to broaden the search.  
- **Domain-specific terminology expansion** – cover specialized jargon or acronyms specific to your domain.  
- **Schema alignment** – map natural language concepts to the actual field names or structures in the database.

> [!WARNING]
> Without query expansion, a user searching for "electronics" might get zero results if your database only contains categories like "telefonia" or "eletronicos" (Portuguese terms). Always expand across language or terminology gaps to ensure the query hits relevant data.

### Cross-Language Expansion (English → Portuguese Categories)

When users search in English but your database uses Portuguese category names (as in Olist), query expansion can translate the terms appropriately. In this example, we map an English category term to the most likely Portuguese category and then use it in an SQL filter:

```python
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI()

# Define structured output for category mapping
class CategoryMapping(BaseModel):
    original_term: str = Field(..., description="The original English search term")
    mapped_categories: list[str] = Field(..., description="Matching Portuguese categories from the available list")
    explanation: str = Field(..., description="Brief explanation of why these categories match")

# Available Portuguese categories in Olist
categories = ["beleza_saude", "eletronicos", "telefonia", "utilidades_domesticas", 
              "moveis_decoracao", "esporte_lazer", "informatica"]

# Prepare the system prompt for mapping
mapping_prompt = f"""
You are a translator for e-commerce product categories between English and Portuguese.
Available Portuguese categories in the database: {', '.join(categories)}

Map the user's search term to the most appropriate Portuguese category or categories.
Only return categories from the available list.
"""

# Process an example user query
user_query = "electronics under 100 BRL"
english_category = "electronics"  # This could be extracted from the query
# Generate the category mapping
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": mapping_prompt},
        {"role": "user", "content": f"Map this English term: '{english_category}'"}
    ],
    response_format=CategoryMapping,
)

mapping = response.choices[0].message.parsed

print(f"Original term: {mapping.original_term}")
print(f"Mapped categories: {mapping.mapped_categories}")
print(f"Explanation: {mapping.explanation}")

# Use the mapped categories in a SQL query (for the price filter extracted from the query)
mapped_categories = mapping.mapped_categories
price_limit = 100  # extracted from "under 100 BRL"

# Construct the SQL with the mapped categories
category_conditions = " OR ".join([f"product_category_name = '{cat}'" for cat in mapped_categories])
sql_query = f"""
SELECT * FROM products 
WHERE ({category_conditions}) AND price < {price_limit}
ORDER BY price DESC;
"""

print("\nGenerated SQL:")
print(sql_query)
```

> [!TIP]
> For more robust category mapping, you can also provide a few-shot example in the prompt. For instance, include example mappings like: *"kitchen stuff" → `utilidades_domesticas`*, *"beauty items" → `beleza_saude`*. Showing a couple of examples helps the model learn common translation patterns.

### Domain-Specific Term Expansion

For specialized domains, LLMs can generate a comprehensive set of related terms to make searches more robust. For example, imagine expanding a financial term into various related metrics:

```python
from pydantic import BaseModel, Field
from openai import OpenAI
from typing import List

client = OpenAI()

# Define structured output for term expansion
class TermExpansion(BaseModel):
    original_term: str = Field(..., description="The original search term")
    synonyms: List[str] = Field(..., description="Direct synonyms and alternative phrasings")
    related_concepts: List[str] = Field(..., description="Related concepts and terminology")
    specific_examples: List[str] = Field(..., description="Specific examples or instances of this concept")

# Example term in a financial context
search_term = "profitability metrics"

# Generate expanded terms for the financial domain
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a financial terminology expert. Expand the given term with related financial concepts."},
        {"role": "user", "content": f"Expand this financial term: '{search_term}'"}
    ],
    response_format=TermExpansion,
)

expansion = response.choices[0].message.parsed

print(f"Original term: {expansion.original_term}")
print(f"Synonyms: {expansion.synonyms}")
print(f"Related concepts: {expansion.related_concepts}")
print(f"Specific examples: {expansion.specific_examples}")

# Suppose we have a list of available database column names (for illustration)
financial_columns = ["gross_profit_margin", "net_income", "ebitda_ratio", "return_on_equity", 
                    "profit_percentage", "revenue_growth", "operating_expenses"]

# Find which expanded terms match our database columns
all_terms = expansion.synonyms + expansion.related_concepts + expansion.specific_examples
matching_columns = []

for term in all_terms:
    for column in financial_columns:
        if any(word.lower() in column.lower() for word in term.split()):
            matching_columns.append(column)

# Remove duplicates
matching_columns = list(set(matching_columns))

print(f"\nMatching database columns: {matching_columns}")

# Construct an example SQL using the matching columns
sql_query = f"""
SELECT 
    {', '.join(matching_columns)} 
FROM financial_reports 
WHERE report_date BETWEEN '2023-01-01' AND '2023-12-31';
"""

print("\nGenerated SQL:")
print(sql_query)
```

> [!CAUTION]
> When expanding financial or other highly technical terms, incorrect mappings can lead to inaccurate calculations or reports. Always have domain experts review and validate expanded terms before using them in production.

### Combined Approach for E-commerce

For a comprehensive solution, you can combine different expansion techniques. The following example extracts key terms from a query, performs cross-language expansion for categories, and generates the final SQL:

```python
from pydantic import BaseModel, Field
from openai import OpenAI
from typing import List, Dict

client = OpenAI()

# Define structured output for a full query processor
class QueryProcessor(BaseModel):
    original_query: str = Field(..., description="The original user query")
    extracted_terms: Dict[str, str]    = Field(..., description="Key terms extracted from the query with their type (category, price, etc.)")
    expanded_categories: List[str] = Field(..., description="Expanded category terms in Portuguese")
    generated_sql: str = Field(..., description="The final SQL query based on all expansions")

# Process a complex user query comprehensively
user_query = "I want cheap electronics and kitchen items with good reviews"

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": f"""
        You process e-commerce queries for the Olist database. 
        Available Portuguese categories: beleza_saude, eletronicos, telefonia, utilidades_domesticas, moveis_decoracao.
        Database columns include: product_id, product_category_name, price, review_score.
        Extract key terms, map categories to Portuguese, and generate the SQL query.
        """},
        {"role": "user", "content": user_query}
    ],
    response_format=QueryProcessor,
)

result = response.choices[0].message.parsed

print(f"Original query: {result.original_query}")
print(f"Extracted terms: {result.extracted_terms}")
print(f"Expanded categories: {result.expanded_categories}")
print("\nGenerated SQL:")
print(result.generated_sql)
```

By using these query expansion techniques (paired with structured output), your prompt-to-SQL system will translate natural language into accurate and comprehensive SQL queries much more effectively.

## Chain-of-Thought & Debugging

### Handling Chain-of-Thought

Including the chain-of-thought (reasoning steps) in your structured output can be useful for internal debugging, but you should control its visibility. Some best practices:

- **Keep steps short** – e.g. “step 1: join reviews with order_items,” “step 2: group by category,” etc.  
- **Hide in logs** – In production, log the reasoning steps internally but present only the final answer to the end user.  
- **Be mindful** – LLMs sometimes produce incorrect or partial reasoning. Never treat the chain-of-thought as guaranteed truth.

> [!CAUTION]
> Adding the custom Chain-of-Thought can break the natural reasoning process of the model and it could cause degradation of model's performance.


### Debugging & Observability

1. **Logging** – Always log your prompts and the model’s raw responses during development. If the JSON output is invalid, inspecting the log lets you see exactly what was returned.  
2. **OpenTelemetry** – Use OpenTelemetry to instrument the OpenAI calls and collect metrics like token usage, latency, and error codes. This helps you monitor performance and detect issues.  
3. **Error Handling** – If the model’s structured output is incomplete or if the request triggers a refusal, catch it and handle it gracefully (e.g. fall back to a default response or error message).

#### Example Instrumentation

```python
import json
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from openai import OpenAI
from pydantic import BaseModel, Field

# SQL query generation output format
class SQLGeneration(BaseModel):
   sql_query: str = Field(..., description="The final SQL query (PostgreSQL syntax)")

# Set up HTTPX instrumentation to trace requests
HTTPXClientInstrumentor().instrument(
   request_hook=lambda span, request: print(json.dumps(json.loads(b''.join(chunk for chunk in request.stream).decode('utf-8')), indent=2))
)

# Create the OpenAI client after instrumentation
client = OpenAI()
messages = [
   {"role": "system", "content": "You are a SQL expert for the Olist e-commerce database."},
   {"role": "user", "content": "What's the average review score for 'beleza_saude' products?"},
   {"role": "assistant", "content": "SELECT AVG(r.review_score) AS avg_score FROM order_reviews r JOIN order_items oi ON r.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'beleza_saude';"},
   {"role": "user", "content": "Which product category has the highest rate of 5-star reviews?"}
]

# Generate SQL for the new question
completion = client.beta.chat.completions.parse(
   model="gpt-4o",
    messages=messages,
    response_format=SQLGeneration
)

print(completion.choices[0].message.parsed.sql_query)
```

With this instrumentation, you’ll see detailed traces of each API request in your console (which you could also forward to your logging system).


## Practical Assignment: Enhance Your Prompt-to-SQL Pipeline

### What to Do

1. **Refactor** your existing code to use Pydantic models and the `response_format` from the OpenAI Beta API.  
2. **Embed 2–3 examples** (few-shot) into your prompt for each tricky question to guide the model toward correct answers.  
3. **Implement Query Expansion** for product categories. In other words, translate English category terms in user queries into their Portuguese equivalents in the SQL filter.  
4. **Optional** – Add a short `steps` field to your structured output to capture the model’s reasoning. Keep this for internal use only; user-facing answers should remain clean.  
5. **Debug** thoroughly: enable logging, handle malformed or partial outputs gracefully, and watch out for rate limits or other performance issues.

### Goals

- **Achieve 10/10** correctness on the original Olist queries (such as “What percentage of orders are delivered before the estimated date?”).  
- **Accept** user queries that reference categories in English or use synonyms for category names.  
- **Produce** valid, parseable JSON output (no more post-hoc string slicing!).  
- **Log & Monitor** the system for performance and handle any unexpected edge cases.

**Remember:** The best results come from iterating on your few-shot examples and refining your schema fields to fit your real data needs.


## References

1. **Official OpenAI Docs**
    - [Structured Outputs in the API](https://openai.com/index/introducing-structured-outputs-in-the-api/)
    - [OpenAI DevDay 2024 – Example Video](https://youtu.be/kE4BkATIl9c)
    - [Pydantic & Beta Response Formats](https://platform.openai.com/docs/guides/structured-outputs)
2. **Query Expansion:** [Haystack Intro](https://haystack.deepset.ai/blog/query-expansion)  
3. **OpenTelemetry:** [Instrumenting HTTPX Calls](https://opentelemetry.io/docs/instrumentation/python/)  

---

**That’s it!** By adding structured outputs, few-shot examples, English-to-Portuguese query expansion, and chain-of-thought debugging, you’re taking your Olist pipeline to the next level—aiming for **10/10** query accuracy, more robust search, and minimal headaches.

**Happy Coding & Good Luck!**  

---
❤️ **LLM LAB – 2025**
