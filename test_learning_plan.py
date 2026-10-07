from assessment.ai_generator import generate_learning_plan


student_data = """
Topic: Python Exception Handling

Current Score: 52%

Previous Scores:
45%, 48%, 52%

Easy Questions Average: 65%

Medium Questions Average: 45%

Hard Questions Average: 30%

Completed Easy Content: No

Completed Medium Content: No

Completed Advanced Content: No

Learning Trend: Improving

Weak Concepts:
- try and except
- finally
- raise
- custom exceptions
"""


plan = generate_learning_plan(student_data)


print("=" * 60)
print("COGNIFYAI ADAPTIVE LEARNING PLAN")
print("=" * 60)

print()

print("Topic:", plan.topic)
print("Score:", plan.current_score)
print("Current Level:", plan.current_level)
print("Next Level:", plan.next_level)

print()

print("Summary:")
print(plan.learning_summary)

print()

print("Priority Concepts:")
for concept in plan.priority_concepts:
    print("-", concept)

print()

print("Recommended Mode:")
print(plan.recommended_mode)

print()

print("EASY:")
print("Status:", plan.easy.status)

for item in plan.easy.recommended_content:
    print("-", item)

print()

print("MEDIUM:")
print("Status:", plan.medium.status)

for item in plan.medium.recommended_content:
    print("-", item)

print()

print("ADVANCED:")
print("Status:", plan.advanced.status)

for item in plan.advanced.recommended_content:
    print("-", item)

print()

print("REAL WORLD PROBLEM:")
print(plan.real_world_problem.title)

print(plan.real_world_problem.description)

print("Difficulty:",
      plan.real_world_problem.difficulty)

print()

print("NEXT ACTION:")
print(plan.next_action)