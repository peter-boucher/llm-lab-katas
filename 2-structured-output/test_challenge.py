import main
# The LLM should be able to generate SQL queries to answer the following questions correctly:

def test_1():
    question = "Which seller has delivered the most orders to customers in Rio de Janeiro? [string: seller_id]"
    answer = main.answer_question(question)
    assert "4a3ca9315b744ce9f8e9374361493884" in str(answer)

def test_2():
    question = "What's the average review score for products in the 'beleza_saude' category? [float: score]"
    answer = main.answer_question(question)
    assert "4.14" in str(answer)

def test_3():
    question = "How many sellers have completed orders worth more than 100,000 BRL in total? [integer: count]"
    answer = main.answer_question(question)
    assert "0" in str(answer)

def test_4():
    question = "Which product category has the highest rate of 5-star reviews? [string: category_name]"
    answer = main.answer_question(question)
    assert "beleza_saude" in str(answer)

def test_5():
    question = "What's the most common payment installment count for orders over 1000 BRL? [integer: installments]"
    answer = main.answer_question(question)
    assert "1" in str(answer)

def test_6():
    question = "Which city has the highest average freight value per order? [string: city_name]"
    answer = main.answer_question(question)
    assert "itupiranga" in str.lower(str(answer))

def test_7():
    question = "What's the most expensive product category based on average price? [string: category_name]"
    answer = main.answer_question(question)
    assert "pcs" in str(answer)

def test_8():
    question = "Which product category has the shortest average delivery time? [string: category_name]"
    answer = main.answer_question(question)
    assert "artesanato" in str(answer)    

def test_9():
    question = "How many orders have items from multiple sellers? [integer: count]"
    answer = main.answer_question(question)
    assert 1278 == answer.iat[0, 0] 

def test_10():
    question = "What percentage of orders are delivered before the estimated delivery date? [float: percentage]"
    answer = main.answer_question(question)
    assert 88.0 <= answer.iat[0, 0] <= 92.0
