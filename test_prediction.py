from dashboard.services.prediction import generate_predictions

temperatures = [25.0] * 24

results = generate_predictions(
    temperatures=temperatures,
    is_holiday=0
)

for item in results:
    print(item)