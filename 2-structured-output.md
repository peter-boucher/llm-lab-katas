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

client = OpenAI()

messages = [
    {"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
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
> Use `Field(..., description="Extra instruction for this field only")` to add the extra prompt for a specific field. Such field prompts could completely replace the `system` prompt.
> Funny enough, this field descriptions are not counted in consumed tokens, so sometimes this can be a nice strategy to save tokens.
> But this could cause delays in compiling schemas for the first time (sometimes up to several minutes for really large Pydantic models); then these compiled models cached globally.


This approach yields a small chain-of-thought in `"steps"` plus the final `sql_query`.

> [!CAUTION]
> In **production** contexts, you often keep chain-of-thought hidden from end-users due to possible inaccuracies or security concerns. But for internal debugging or educational uses, it’s helpful!

---

## 2. Few-Shot Learning

**What is it?**  
Few-shot learning is a technique where we provide the LLM with 2-3 example question-answer pairs to guide its responses. This helps the model understand the expected format, style, and logic for generating SQL queries specific to your database schema.

**Why use it?**  
By showing concrete examples of correct SQL queries for your database, you reduce schema hallucinations, teach the model how to handle specific joins and table relationships, and demonstrate preferred SQL style and patterns.

> [!TIP]
> The quality of your few-shot examples significantly impacts model performance - use expert-validated and well-tested SQL queries to avoid degradation of prompt quality.

### Multiple Ways to Incorporate Few-Shot Examples

There are several effective approaches to implementing few-shot learning in your prompt-to-SQL pipeline:

#### Mimic Assistant Answers to User Queries

You can include examples directly in the chat history:

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
    {"role": "user", "content": f"{user_question}"}
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
> This approach creates a fake chat history which LLM uses to generate the next answer.

#### 2. Chat History and Iterative Feedback Refinement

The chat history approach can be combined with iterative feedback to create a powerful self-improving system:

```python
from pydantic import BaseModel, Field
from openai import OpenAI
import json

client = OpenAI()

# Define our structured output format
class SQLGeneration(BaseModel):
    reasoning: list[str] = Field(..., description="Short reasoning steps explaining the approach")
    sql_query: str = Field(..., description="The final SQL query (PostgreSQL syntax)")

# Function to evaluate SQL quality
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

# Maintaining a growing conversation with feedback
def build_conversation_with_feedback(test_queries, correct_sql_map, system_prompt):
    """Build a conversation history with automatic feedback for improvement"""
    
    conversation = [{"role": "system", "content": system_prompt}]
    
    for query_desc, query in test_queries.items():
        # Add the user question
        conversation.append({"role": "user", "content": query})
        
        # Get model response
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=conversation,
            response_format=SQLGeneration
        )
        
        generated_sql = response.choices[0].message.parsed.sql_query
        correct_sql = correct_sql_map[query_desc]
        
        # Evaluate the SQL
        evaluation = evaluate_sql(generated_sql, correct_sql, query_desc)
        
        # Add model's response to history
        conversation.append({
            "role": "assistant", 
            "content": generated_sql
        })
        
        # If SQL was incorrect, add feedback to improve future responses
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
> This automated feedback approach works particularly well for production systems where you want to continuously improve performance based on evaluation data without manually rewriting prompts.


## 3. Query Expansion

**What is it?**  
Query expansion is a technique that enhances the original user query with additional related terms, synonyms, or contextual information. This improves search coverage by bridging the gap between how users naturally express their needs and how data is structured in your database.

**Key Use Cases:** This includes cross-language mapping between user terms and database terms (e.g., English to Portuguese), synonym expansion to increase search coverage, domain-specific terminology expansion, and schema alignment that maps natural language concepts to database structure.

> [!WARNING]
> Without query expansion, users searching with English terms like "electronics" may get zero results if your database uses terms like "telefonia" or "eletronicos" in Portuguese. Always expand terms across language or terminology gaps.

### 3.1 Cross-Language Expansion (English → Portuguese Categories)

When users search in English but your database uses Portuguese category names (as in Olist), query expansion translates the terms appropriately.

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

# Create the mapping prompt
mapping_prompt = f"""
You are a translator for e-commerce product categories between English and Portuguese.
Available Portuguese categories in the database: {', '.join(categories)}

Map the user's search term to the most appropriate Portuguese category or categories.
Only return categories from the available list.
"""

# Process the user query
user_query = "electronics under 100 BRL"
english_category = "electronics"  # This could be extracted programmatically

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

# Use the mapped categories in your SQL query
mapped_categories = mapping.mapped_categories
price_limit = 100  # Extracted from "under 100 BRL"

# Construct the SQL with mapped categories
category_conditions = " OR ".join([f"product_category_name = '{cat}'" for cat in mapped_categories])
sql_query = f"""
SELECT * FROM products 
WHERE ({category_conditions}) AND price < {price_limit}
ORDER BY price DESC
"""

print("\nGenerated SQL:")
print(sql_query)
```

> [!TIP]
> For more robust category mapping, include a few-shot approach where you show examples of previous mappings: "kitchen stuff" → `utilidades_domesticas`, "beauty items" → `beleza_saude`. This helps the model learn common cross-language patterns.

### 3.2 Domain-Specific Term Expansion

For specialized domains, you can use LLMs to generate comprehensive sets of related terms for more robust searching:

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

# Example for financial domain
search_term = "profitability metrics"

# Generate expanded financial terms
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

# Available database columns (simulated)
financial_columns = ["gross_profit_margin", "net_income", "ebitda_ratio", "return_on_equity", 
                    "profit_percentage", "revenue_growth", "operating_expenses"]

# Find matching columns across all expanded terms
all_terms = expansion.synonyms + expansion.related_concepts + expansion.specific_examples
matching_columns = []

for term in all_terms:
    for column in financial_columns:
        if any(word.lower() in column.lower() for word in term.split()):
            matching_columns.append(column)

# Remove duplicates
matching_columns = list(set(matching_columns))

print(f"\nMatching database columns: {matching_columns}")

# Generate SQL with expanded columns
sql_query = f"""
SELECT 
    {', '.join(matching_columns)} 
FROM financial_reports 
WHERE report_date BETWEEN '2023-01-01' AND '2023-12-31'
"""

print("\nGenerated SQL:")
print(sql_query)
```

> [!CAUTION]
> When expanding financial or highly technical terminology, be aware that incorrect mappings can lead to inaccurate financial calculations or reporting. Always validate expanded terms with domain experts before using in production.

### 3.3 Combined Approach for E-commerce

For a comprehensive solution, you can combine different expansion techniques:

```python
from pydantic import BaseModel, Field
from openai import OpenAI
from typing import List, Dict

client = OpenAI()

# Define structured output for comprehensive query processing
class QueryProcessor(BaseModel):
    original_query: str = Field(..., description="The original user query")
    extracted_terms: Dict[str, str] = Field(..., description="Key terms extracted from the query with their type (category, price, condition, etc.)")
    expanded_categories: List[str] = Field(..., description="Expanded category terms in Portuguese")
    generated_sql: str = Field(..., description="The final SQL query based on all expansions")

# Process user query comprehensively
user_query = "I want cheap electronics and kitchen items with good reviews"

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": f"""
        You process e-commerce queries for the Olist database. 
        Available Portuguese categories: beleza_saude, eletronicos, telefonia, utilidades_domesticas, moveis_decoracao.
        Database columns: product_id, product_category_name, price, review_score.
        Extract key terms, map to Portuguese categories, and generate SQL.
        """},
        {"role": "user", "content": user_query}
    ],
    response_format=QueryProcessor,
)

result = response.choices[0].message.parsed

print(f"Original query: {result.original_query}")
print(f"Extracted terms: {result.extracted_terms}")
print(f"Expanded categories: {result.expanded_categories}")
print(f"\nGenerated SQL:")
print(result.generated_sql)
```

By implementing these query expansion techniques with structured output, your prompt-to-SQL system can significantly improve translation of natural language to accurate and comprehensive SQL statements.


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
import json
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from openai import OpenAI
from pydantic import BaseModel, Field

# SQL query generation output format
class SQLGeneration(BaseModel):
   sql_query: str = Field(..., description="The final SQL query (PostgreSQL syntax)")

# Set up telemetry
HTTPXClientInstrumentor().instrument(
   request_hook=lambda span, request: print(json.dumps(json.loads(b''.join(chunk for chunk in request.stream).decode('utf-8')), indent=2))
)

# Create client after instrumentation
client = OpenAI()
messages = [
   {"role": "system", "content": "You are a SQL expert for the Olist e-commerce database."},
   {"role": "user", "content": "What's the average review score for 'beleza_saude' products?"},
   {"role": "assistant", "content": "SELECT AVG(r.review_score) AS avg_score FROM order_reviews r JOIN order_items oi ON r.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE p.product_category_name = 'beleza_saude';"},
   {"role": "user", "content": "Which product category has the highest rate of 5-star reviews?"}
]

# Generate SQL
completion = client.beta.chat.completions.parse(
   model="gpt-4o",
   response_format=SQLGeneration,
   messages=messages
)

print(completion.choices[0].message.parsed.sql_query)
```

You’ll see traces in your console for each request (can enable for logging as well).

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
