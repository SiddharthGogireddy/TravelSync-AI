from    backend.services.trip_editor.llm_interpreter import interpret_trip_prompt

result = interpret_trip_prompt(
    "Add Charminar, remove Golconda Fort, set my budget to ₹30000 and regenerate day 2"
)

print("\nFINAL RESULT:")
print(result)