import requests

url = "http://localhost:8000/api/shipments/upload/"
file_path = "SAP_Consignment_Overview (96).xlsx"

with open(file_path, "rb") as f:
    response = requests.post(url, files={"file": f})

print("Status:", response.status_code)
print("Response:", response.json())
