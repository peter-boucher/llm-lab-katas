# ❤️ Evaluations and Feedback Loops for LLM Products

### Introduction

So far, you’ve built and refined an LLM-to-SQL pipeline for the Olist e-commerce dataset. Now it’s time to answer a critical question: **How do we know our LLM-powered solution is actually working well?** This is where **evaluations (evals)** come into play. LLM evals help assess an AI product’s performance to ensure its outputs are accurate, safe, and aligned with user needs. In a large enterprise like Maersk with dozens of LLM-driven apps, systematic evals are the only way to track quality across the board. Evals in this context are not about testing the _model_ in isolation, but about testing the _entire product workflow_ – from prompt design to model output to post-processing and feedback integration.

Think of LLM product evals as our unit tests and monitoring system rolled into one. They help us catch regressions when we update a prompt or switch to a new model version, and they shine light on weaknesses (e.g. certain query types that consistently fail). Without evals, it’s difficult and time-consuming to understand how changes in the model or prompts affect your use case. As OpenAI’s devs put it, crafting good evals is one of the most impactful things you can do when building with LLMs. In a company setting, this translates to fewer firefights in production and more confidence when deploying AI features.

**Start simple.** It’s tempting to over-engineer an evaluation harness from day one, but initially a simple checklist or a small set of test cases will do. For example, begin with a handful of representative input questions and expected outputs saved in a CSV file or even just a Python list. This “mini-benchmark” will be the seed of your eval suite. The key is to cover the core scenarios your product _must_ handle correctly (e.g. basic SQL queries in our case) and a couple of edge cases. Evals are not one-and-done – you’ll **grow** them over time as your application evolves. In fact, an eval set should be a living thing: as new user requests or failure modes surface, you add them to your tests. Over weeks and months, a simple eval list might expand to dozens or hundreds of cases, each teaching your LLM system what “good” looks like and guarding against future mistakes.

Before we dive in, an important mindset: we are evaluating **LLM products**, not just LLM models. Traditional model benchmarking (think academic leaderboards) focuses on general capabilities with static datasets, treating the model as the end-all. Here, we’re concerned with end-to-end **product behavior**. That means considering everything from prompt templates and chain-of-thought logic to how the output is used downstream. An LLM product eval asks _“Does the system solve the user’s problem reliably and safely?”_ rather than _“Is the model’s perplexity low?”_. This shift in perspective will guide how we design our tests.

---

### Evals 101: From Simple Tests to Production Benchmarks

The simplest eval is hardly different from a unit test. Give the LLM pipeline an input and check if the output meets expectations. For structured tasks like SQL generation, this could be as straightforward as verifying the query result or comparing the output SQL to a known correct answer. For example, if the question is _“How many sellers have more than 100,000 BRL in total sales?”_, we might expect the SQL to include a `COUNT` on sellers with a `SUM > 100000`. A basic eval could run the generated SQL on a test database and see if the returned count matches an expected value. If it does for all our test questions – great, we’re on the right track.

Early on, a small set of high-value test cases provides outsized benefits. It’s more useful to have 5-10 carefully chosen queries that cover different corners of your problem (aggregations, filters, edge phrasing, etc.) than 100 trivial variations. Each eval case should ideally check a distinct aspect of correctness or robustness. In our Olist scenario, for instance, one case might check a straightforward selection ("List the top 5 customers by spend"), another might check a tricky filter condition ("Orders delivered late in São Paulo"), and another might intentionally probe a potential weakness (like a prompt that could cause the model to produce an invalid column name). By starting with a small diverse set, you create a safety net for your development: any change to the pipeline (a new prompt format or switching from GPT-4 to GPT-4.5) can be validated against these examples to catch regressions quickly.

As your application scales, so should your evals. Over time, what begins as a simple checklist can evolve into a comprehensive regression test suite. Large companies often maintain a library of eval scenarios for each AI product – effectively a custom benchmark tailored to the business. Unlike one-off model benchmarks, these evals are **scenario-based** and tied closely to real user needs. A customer support chatbot at Maersk might have evals for common inquiries, rare but important edge cases (e.g. policy-related questions), and even past incidents that went wrong (to ensure _those_ don’t happen again). This library becomes a powerful asset: it lets developers quickly measure if an update is an improvement or if it breaks something that used to work.

### Structured vs. Unstructured Outputs

Not all LLM outputs are created equal when it comes to evaluation. **Structured outputs** (like SQL queries, JSON, lists of facts, code) are comparatively easier to evaluate automatically. Since these outputs have a defined format or objective truth, we can write deterministic checks. For SQL, we can run the query and compare results to a ground truth answer. For JSON outputs, we can validate the JSON schema (using `Structured Output API`) and contents against expected values. If our LLM is supposed to return a structured object, we can often tell programmatically if it’s correct or not (did it include the required fields? do numeric fields have realistic values? etc.). In our SQL generator, a structured eval might look like: does the SQL run without error, and does it retrieve the correct data for the given question?

On the other hand, **unstructured outputs** (like free-form explanations, summaries, or recommendations) are trickier. There might be many acceptable answers phrased in different ways, or the criteria for success might be subjective (e.g. tone, clarity). Evaluating these often requires semantic comparison or human judgment. For instance, if the task is summarizing a shipping report, there isn’t a single “correct” summary, but we can evaluate whether the summary captures the key points. Automated metrics for unstructured text (think BLEU, ROUGE for summaries, or similarity scores) can give a rough idea but often miss nuance. Another approach is using LLMs to judge LLM outputs (e.g. GPT-4 scoring an answer for accuracy and completeness), sometimes called _LLM-as-a-judge_. This can work at scale but may introduce its own biases and needs careful prompt design to be reliable.

**Key point:** start with straightforward checks for structured parts of your output, and use simple heuristic metrics for unstructured parts. Don’t let the perfect be the enemy of the good; a rough automatic check is better than none. For example, you might begin by having your code verify that the word _“DELETE”_ does not appear in a generated SQL (a basic safety check) for adversarial prompts, or that an answer citing a document actually includes a reference to that document. These are binary yes/no checks – easy to implement and fast to run. As you gather more outputs, you might then incorporate more nuanced evaluations (like checking factual accuracy of an open-ended answer by cross-verifying with a knowledge base).

**Evolving Your Evaluation Strategy**

Your evaluation approach should **evolve with your product**. Early on, the focus is on _capabilities_ – can the system do what it’s supposed to do? (Does the SQL query answer the question correctly? Does the chatbot actually book the cargo shipment when asked?) As those fundamentals solidify, you start caring about finer details and _risks_ – is it doing things safely and responsibly? (Does the SQL avoid destructive commands? Is the chatbot refraining from giving confidential info?). Initially, you might ignore the style of the answer as long as it’s correct; later, you might add eval criteria for tone and format once accuracy is consistently high.

A good practice is to periodically perform **error analysis** on your eval results. Whenever a test fails, dig into why. Was the prompt unclear? Did the model misunderstand the question? Or is the expected answer itself debatable? By classifying the failures, you can often identify themes: for example, maybe all failures involve date filters, or the model struggles with a specific product category name. This insight helps you decide the next course of action – maybe you need to add a few-shot example demonstrating a date filter, or adjust the prompt to clarify how to handle that category. It could also reveal issues in your eval set; perhaps the “expected answer” was actually wrong or there are multiple correct answers (requiring the eval logic to be more forgiving).

Keep in mind that LLM product evals are not static like a traditional test suite. They should be continually updated to reflect new knowledge and requirements (like 15 min morning routine). If tomorrow your database schema changes or you add a new feature (say, handling queries about a new data field), your evals need to expand to cover that. Likewise, if you discover a new failure mode in production (e.g. a user phrasing that confuses the model), consider adding a test for it so it doesn’t slip through in the future. Many teams adopt a cadence (for example, weekly or bi-weekly) to review recent outputs, update eval cases, and re-run the suite. Over time this creates a robust regression test bed. By the time you have dozens of LLM apps in a company, each with its own eval suite, you’ll likely also establish some centralized tools or dashboards to track all this (and avoid reinventing the wheel for each project). We’ll touch on some tools and frameworks that can help in the References.

Before moving on, note that evaluation for LLM products often doesn’t boil down to a single number like accuracy. You might track a few metrics: e.g. _accuracy_ (percentage of test cases with correct output), _robustness_ (ability to handle slightly perturbed inputs), and _safety_ (rate of flagged unsafe outputs). In practice, you’ll have a mix of automated tests and **manual reviews**. Let’s talk about that “human in the loop” aspect next, because not everything can be caught by code.

---
### Expert-in-the-Loop: Leveraging Human Feedback

Even the best automated eval metrics will only get you so far. AI products, especially in complex domains, benefit greatly from having an expert (or actually, **experts**) in the loop. What does this mean? In short, a human domain expert reviews some of the AI’s outputs and provides feedback – identifying errors, rating quality, or suggesting improvements. This is the old concept of human QA (Quality Assurance) applied to AI, and it’s incredibly powerful when used well.

Early in your project, expert-in-the-loop might look like this: you, as the developer, manually inspect the outputs for your 10 test questions and see if the SQL and results make sense. Essentially, _you_ are the human evaluator at first. As the project grows, you might involve others – say a senior data analyst or a subject matter expert in logistics – to periodically audit the AI’s performance. For example, if you built an LLM that answers logistics questions in natural language, a domain expert at Maersk could review a random sample of answers and mark any mistakes or omissions.

The goal of expert feedback is twofold: (1) to catch issues that automated tests miss, and (2) to continually define and refine what “correct” and “excellent” output means for your domain. Unlike a classic software unit test, an LLM’s output might be _technically_ correct but still not ideal. Maybe the SQL query runs but it’s not the most efficient way to get the answer, or the answer is correct but phrased in a way that’s hard for a customer to understand. A human expert can provide nuanced judgment on these aspects (“the answer is right but it’s using jargon – not good for a customer-facing reply”). Those insights can then inform new eval criteria or prompt adjustments.

**How to integrate expert feedback in the eval loop?** Start by making it easy for an expert to review outputs. This could be as simple as sharing a spreadsheet with inputs, model outputs, and a column for the expert to mark “OK/Not OK” or leave comments. For a more advanced setup, you might build an internal tool where the expert can log in and rate each response on several dimensions (e.g. correctness, clarity, completeness, etc.). In either case, keep the interface and criteria clear – the expert should know what to look for. For instance, give them instructions like _“Mark the output incorrect if it misses key info or has any factual error; mark it unsafe if it reveals confidential data or uses harassing language,”_ and so on.

Once you have expert annotations, **feed them back** into your development cycle. Treat the expert-labeled cases as high-priority examples. If an expert flagged an output as wrong, that example should likely join your eval suite as a new test (after you determine the ideal correct output). If they flagged something as unsafe, definitely include a test for that scenario with the expectation that the model should refuse or sanitize the answer. In essence, the expert feedback is generating ground truth data for you. Over time, this yields a much richer eval set than you could have created on your own upfront. It also helps catch drifting behavior – maybe the model was fine on a scenario last month but a new model update caused a subtle error that only a human would notice; the expert-in-the-loop process will highlight that.

#### Best practices for human-in-loop evals:

- **Define clear evaluation criteria:** Ensure that experts know the guidelines. Consistency is key – if you have multiple people reviewing, they should apply the same standards. Consider writing a one-page eval guideline for your product (what constitutes a major vs minor error, etc.).

- **Start small and scale up:** Maybe you begin with one expert reviewing 20 outputs per week. If the product is high stakes, you might scale to have a team of reviewers checking a larger sample or even all outputs above a certain risk threshold. For instance, if an answer will be sent to a customer unvetted, you might have 100% review until trust is built.

- **Use a mix of random and focused sampling:** Don’t only review outputs you suspect are wrong; also sample random outputs to get an unbiased sense of quality. Sometimes the AI will surprise you (both positively and negatively) in areas you weren’t specifically testing.

- **Close the loop:** It’s called expert-in-the-loop because the feedback should loop back into improving the product. This could be by updating prompts, adding more few-shot examples, adjusting system instructions, or even fine-tuning the model if you have that capability. Over time, the need for correction should start to diminish in areas that were actively trained/evaluated, letting the experts focus on new challenges.

One thing to remember: **manual evaluation is costly** – it takes time and expert attention. So, use it thoughtfully. Automate whatever you can, and reserve the expert reviews for things that truly need human judgment or for validating the automated metrics themselves. Many teams use manual evals as a periodic calibration. For example, if your automated tests say “90% of outputs are good,” you might still do a manual sweep to confirm that quality in reality. If the manual check finds only 70% are truly good, then your automated eval criteria might need refinement. This balance of automated and manual is the art of LLM product evaluation.

---

### Hands-On: Evaluating the Question-to-SQL Pipeline

Time to get our hands dirty with a concrete example. We’ll continue with our Olist **question-to-SQL** app from the previous lessons. By now, you have a pipeline where a user question (in English) goes through an LLM and comes out as a SQL query (possibly with a few reasoning steps if you kept those). Let’s build a simple evaluation harness for this pipeline.

##### 1. Define some test cases

We’ll use a few questions from our original assignment (you had 10 core questions there). For illustration, let’s take two example questions:

- _Question 1:_ **“Which seller has delivered the most orders to customers in Rio de Janeiro?”**

_Expected outcome:_ The ID of the seller with the highest count of orders delivered to Rio. (We might not know the ID offhand without running a SQL ourselves, but we know the form of the answer should be a single seller_id.)

- _Question 2:_ **“What’s the average review score for products in the ‘beleza_saude’ category?”**

_Expected outcome:_ A numeric value (floating-point) representing the average review score for that category, e.g. something like 4.3.

In a real eval, we’d have the exact expected answers (either the correct SQL query or the correct result). For now, let’s assume we have a way to get the ground truth – maybe by writing our own SQL queries or using a trusted data analyst’s answer.

##### 2. Run the pipeline on each test and capture the output
In code, this might look like a simple loop that sends each question to your generate_sql() function (which internally calls the LLM) and then collects the outputs:

```
test_cases = [
    {
        "question": "Which seller has delivered the most orders to customers in Rio de Janeiro?",
        "expected": "seller_123"  # placeholder for the actual seller_id expected
    },
    {
        "question": "What's the average review score for products in the 'beleza_saude' category?",
        "expected": 4.3  # placeholder expected value
    }
]

for case in test_cases:
    q = case["question"]
    expected = case["expected"]
    output = generate_sql(q)  # This calls the LLM to get SQL (and maybe executes it)
    print(f"\nQ: {q}\nGenerated SQL: {output}")
```

For our purposes, let’s say generate_sql(q) returns just the SQL string. We print it out to see what the model did.

##### 3. Basic correctness check
Now that we have the SQL, how do we evaluate it? If we have an expected SQL query or result, we can compare. One robust method is to actually run the SQL against a test database (a safe copy of the Olist database) and get the result, then compare that result to the expected answer. Another quicker method (though less reliable) is string comparison of SQL or checking certain keywords. Let’s illustrate the execution approach:

```
result = execute_sql(output)  # runs the query on a test DB and returns the result
if result == expected:
    print("✅ Pass")
else:
    print(f"❌ Fail: expected {expected}, got {result}")
```

If the question expects a single value (like the average score), result might be that number. For a more complex query (like the seller with most orders), result might be a row or value that we can compare to the expected seller ID.

##### 4. Safety checks
Besides correctness, we want to flag any _dangerous or undesirable_ outputs. In our SQL case, that means ensuring the LLM doesn’t produce commands that could harm the database or violate rules. We definitely don’t want our model deciding to DROP a table or DELETE records! We can add a simple heuristic check for forbidden keywords:

```
dangerous = False
for keyword in ["DROP", "DELETE", "ALTER", "UPDATE"]:
    if keyword in output.upper():
        dangerous = True
        break

if dangerous:
    print("⚠️  Potentially destructive SQL detected!")
```

This snippet scans the generated SQL for any occurrence of words like DROP, DELETE, ALTER, or UPDATE (we uppercase the output to catch any case variations). If we find any, we flag it. In a full system, you might have the pipeline refuse to execute such queries or send them for manual review. For eval purposes, we simply note that such a case is an automatic failure (the model _should never_ produce these in our use case which is read-only analytics).

##### 5. Schema/format checks
Another structured output check: does the SQL even parse? If the model returned malformed SQL (say, a missing comma or a completely non-SQL answer), that’s a failure. If you’re executing the query as above, a syntax error will show up when execute_sql runs – which you can catch as an exception and mark the eval as failed due to invalid SQL. Alternatively, if not actually executing, you could at least do a rudimentary validation like ensuring certain expected table or column names are present if the question implies them. For instance, question 2 about 'beleza_saude' should likely reference the products or order items table and the reviews table; if the SQL has no mention of those, it’s probably incorrect.

Let’s simulate what running our two test cases might produce (this is a hypothetical example for illustration):

```
Q: Which seller has delivered the most orders to customers in Rio de Janeiro?
Generated SQL: SELECT seller_id FROM orders JOIN customers ON orders.customer_id = customers.customer_id 
              WHERE customers.city = 'rio de janeiro' 
              GROUP BY seller_id 
              ORDER BY COUNT(*) DESC 
              LIMIT 1
✅ Pass  (expected seller_123, got seller_123)

Q: What's the average review score for products in the 'beleza_saude' category?
Generated SQL: SELECT AVG(review_score) 
              FROM order_reviews JOIN products ON order_reviews.product_id = products.product_id 
              WHERE products.product_category_name = 'beleza_saude';
⚠️  Potentially destructive SQL detected!
❌ Fail: expected 4.3, got 4.1
```

In the made-up output above, the first query was correct and returned the expected seller_id. The second query executed fine and returned 4.1 as the average score, but our expected was 4.3 (so maybe our expected was off, or the model did something slightly differently; we’d investigate why). More alarmingly, we flagged “Potentially destructive SQL” – perhaps our keyword check mistakenly triggered (maybe the model didn’t actually drop anything, or perhaps it tried an UPDATE somewhere). This indicates something to look at: if that flag is true, it’s an automatic fail in our eval report.

##### 6. Logging and iterating.
When you run such evals, always log the outcomes in a clear way. A simple printout as above is fine for initial development. In a more automated eval script, you might accumulate results in a list or data frame, and then print a summary like “8/10 tests passed, 2 failed.” For each failure, log the details (which test, what was expected vs got, and why it failed if known). These logs are gold for debugging. If all tests pass, fantastic – but in reality, you’ll usually have a few failures initially, which is exactly the point. Each failure is a chance to improve your pipeline or your evals.

**Storing the eval cases:** you can keep it simple with a hardcoded list or use a CSV file that your script reads. For instance, eval_cases.csv might have columns: question, expected_result. This makes it easy to add new cases without changing code. Just be cautious to **not** include sensitive data in such files, and if your eval set grows big, you might shift to a database or an internal eval service. But a CSV or JSON file is perfectly fine at the start. (We’ll likely move to a more scalable approach like a feature store or lakehouse in later iterations, but no need to jump there right now.)

**One more thing**: Our current eval is focused on structured output accuracy and obvious safety. In next week’s lesson, we’ll expand into evaluating unstructured outputs (like answers to questions based on documents) where we’ll deal with more subtle criteria. For now, if you have any free-form text outputs in your pipeline (perhaps an explanation field along with the SQL), you could do a very basic check: e.g., ensure the explanation text isn’t empty and perhaps doesn’t contain a known forbidden word. But the heavy lifting for unstructured evals (like checking if a generated explanation actually matches the SQL results or is factually correct) will come later. **Keep the scope small and targeted for now.**

---

### Real-World Tips & Tricks for LLM Product Evals

In building and operating LLM products across various companies, we’ve picked up some handy tips. Here are a few to help you hit the ground running:

- **Test with real data early:** It’s crucial to include actual user queries (or close approximations) in your evals as soon as you can. Synthetic examples are good for initial coverage, but real queries often reveal unanticipated quirks. If your system is already live, start logging anonymized user inputs and outcomes, and turn some of those into eval cases (especially any that went wrong). This keeps your evals grounded in reality.

- **Diversify your eval set:** Make sure your tests aren’t all almost identical. Cover different intents, different input lengths, languages (if applicable), and edge cases. For example, include a test with an empty input or a very long input if your app might encounter those. The more variety, the more confident you can be that a change hasn’t broken something unseen.

- **Beware of overfitting to evals:** One trap in any testing regime is teaching to the test. If you only ever tweak your prompt to get from 8/10 to 10/10 on your current eval set, you might over-optimize for those cases while missing the bigger picture. Occasionally refresh and rotate in new test cases. Also, don’t declare victory just because all tests pass – it should prompt you to expand the tests further or raise the bar on what "pass" means.

- **Automate continuous evaluation:** Just like you’d run unit tests on each code commit, you can automate LLM evals. Tools like **OpenAI Evals** or **DeepEval** can be integrated into pipelines to run eval suites and even generate reports. You can also use CI/CD (Continuous Integration/Delivery) to trigger your eval script whenever the prompt or LLM version changes. This ensures you catch issues _before_ deploying to production. Some teams even integrate evals into a dashboard (e.g., using Weights & Biases or EvidentlyAI) to track metrics over time.

- **Safety and compliance testing:** In enterprise settings, don’t overlook tests for things like data privacy and compliance. If your LLM product interacts with sensitive data, include evals that specifically check that it _doesn’t_ leak that data. For instance, if certain fields (like customer emails) should never appear in output, add a test that intentionally tries to prompt the model to reveal an email and verify it refuses or redacts it. Similarly, if there’s forbidden content categories (like profanity, or advice on illegal activities), set up eval prompts to ensure the model properly refuses or handles them. These evals act as your guardrail audits.

- **Use evals to compare versions:** Whenever a new model update comes (say OpenAI releases GPT-4.5, or you fine-tune a new checkpoint), run your evals on both the old and new versions. This side-by-side comparison is invaluable. It might turn out the new model gets a better overall score but fails one specific query that the old model handled – now you know exactly where to focus (maybe adjust the prompt for that case, or decide the regression is acceptable given the gains). Without evals, these differences can go unnoticed until a user complains.

- **Document and discuss failures:** Treat your evaluation results as a learning tool, not just a report card. Each time you run evals, take a few minutes to note which tests failed and hypothesize why. Share these findings with your team. For example, if your eval shows the model still struggles with a certain product category name, maybe a colleague from that domain can suggest additional phrasing examples to add to the prompt. Over time, you’ll build a playbook of common failure modes and fixes.

---

### Practical Assignment: Evaluate Your LLM Pipeline

Now it’s your turn to put this into action. This week’s assignment is all about setting up a basic evaluation loop for your LLM app and getting some initial metrics. We’ll keep it focused on the structured SQL use case.

**What to Do**

- **Build an Eval Script:** Write a small script or notebook to automate the testing of your prompt-to-SQL pipeline. Use 10-15 questions (start with the ones from the initial assignment, then extend to new cases) as your eval cases. For each, have the script generate the SQL and then execute it on the provided Olist database to fetch the result.

- **Compare Results:** For each query, determine the correct answer (you might need to write your own SQL or look at the data manually for this). Then have your script check whether the LLM-generated SQL’s result matches the expected answer. Log a pass/fail for each test case.

- **Add a Safety Check:** Implement the forbidden word check for SQL (DROP, DELETE, etc.) in your code. Make sure the script flags any query that contains those. (You can even create a _deliberate_ malicious test case, like asking “Delete all orders” to see if your model attempts it – just to verify your guardrail catches it. **Do not run** any such query on the real database, of course – use it solely to test the detection logic.)

- **Record the Outcomes:** Create a simple table or list in your output showing each test case, the expected result, the model’s result, and whether it passed. Note any failures and try to quickly analyze why they failed – this will be useful for discussion.

- **(Optional) Expert Review:** If you have access to a domain expert (or even a colleague) who can act as a second pair of eyes, have them review at least one of your outputs. For example, if a query result seems off, ask them what they would expect. This is just to get a taste of expert-in-the-loop feedback. Incorporate any insights you gain (maybe you add a new test case based on their input).

**Goals**

- **Accuracy Benchmark:** Measure the accuracy of your pipeline on the eval set (e.g., “X out of Y queries were correct”). Even if X is low, that’s fine – you need a baseline to improve upon.

- **Robustness Check:** Ensure that none of the test queries produce dangerous SQL or errors. If any do, that’s a red flag to fix either in the prompt or via guardrails.

- **Logging & Reproducibility:** You should be able to run this eval script repeatedly (especially after making improvements) to verify if things are getting better. Make sure it’s not a one-off – this will be part of your development loop.

- **Reflection:** Identify at least one weakness from the eval results. For instance, maybe the model failed all questions involving a date range. This insight is gold for guiding your next improvement (like adding a few-shot example about date range filtering, or tweaking the prompt instructions).

---

### **References and Further Reading**

1. **OpenAI Evals (Framework)** – _Open-source library for evaluating LLMs and LLM-based systems._ GitHub repo: [openai/evals ](https://github.com/openai/evals). Intro blog and guide: [OpenAI Evals – Getting Started ](https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals).

2. **DeepEval (Confident AI)** – _“Pytest for LLMs” – a framework to unit test LLM outputs._ Introduction: [DeepEval Overview](https://github.com/confident-ai/deepeval). Useful for setting up metrics like G-Eval, hallucination detection, etc., with minimal fuss.

3. **Evidently AI – LLM Evaluation Guide** – _Comprehensive guide on evaluating LLM-powered products._ Covers manual vs automated evals, criteria selection, and more. [LLM Evaluation: A Beginner’s Guide ](https://www.evidentlyai.com/llm-guide/llm-evaluation).

4. **Evidently AI – 7-Day Evaluation Course** – _Free course on LLM evals for product teams._ Youtube playlist [LLM Evaluations Course (Evidently)](https://www.youtube.com/playlist?list=PL9omX6impEuMgDFCK_NleIB0sMzKs2boI) (great for a deeper dive into enterprise eval strategies) plus [slides](extra/03.LLM Evals for AI product teams.pdf) (start from slide 11).

5. **W&B (Weights & Biases) – Evaluating LLMs** – _Techniques and best practices for LLM evals._ (See W&B’s article on [LLM Evaluations: Metrics & Best Practices](https://wandb.ai/onlineinference/genai-research/reports/LLM-evaluations-Metrics-frameworks-and-best-practices--VmlldzoxMTMxNjQ4NA) and how to use their tooling for tracking eval results).

6. **Langfuse – LLM Evaluation 101** – _Blog post on offline vs online evaluation and proven techniques._ [LLM Evaluation 101 (Langfuse)](https://langfuse.com/blog/2025-03-04-llm-evaluation-101-best-practices-and-challenges) – useful to understand evaluation in production environments.

7. **Tanner McRae’s Evaluation Best Practices** – _Medium article on LLM system eval lifecycle._ Emphasizes building custom eval sets (start with ~100 examples, evolve over time). [Evaluating LLM Systems (Medium)](https://medium.com/@tannermcrae/evaluating-llm-systems-best-practices-1bd8e5ac2531).

8. **OpenAI Cookbook – Evaluating GPT-4 for Reliability** – _Guide on how OpenAI suggests evaluating model reliability and identifying weaknesses._ [OpenAI Cookbook: Evaluation Guide](https://cookbook.openai.com/articles/techniques_to_improve_reliability).

9. **Intro To Error Analysis** - Guide on working with unstructured documents, will cover in the next week. [Creating Custom Data Annotation Apps](https://www.youtube.com/watch?v=qH1dZ8JLLdU) plus [slides](extra/03.Getting Started With Error Analysis.pdf). 

---

**That’s a wrap for this lesson!** You learned why evals are the compass guiding your LLM project to success, how to start with simple tests and grow into a robust evaluation workflow, and how to loop in human expertise for that extra quality boost. With a basic eval harness in place, you’re now in a great position to iterate faster and safer on your LLM-powered product.

In the next lesson, we’ll venture into the wild world of unstructured output evaluation – tackling challenges like fact-checking long answers and scoring the quality of document summaries. For now, give yourself a pat on the back for setting up your product’s first evals. This investment will pay off every time you make a change and confidently see those green checkmarks (or catch the reds before they hit production!).

**Happy Evaluating & Keep Building!**

❤️ **LLM LAB – 2025**
