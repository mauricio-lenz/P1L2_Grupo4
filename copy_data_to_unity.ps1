# Refresca el snapshot del contrato que consume Unity (snapshot ignorado excepto el de data/,
# que es la fuente de verdad). Guarda + Test Runner en Unity después de copiar.
Copy-Item "data\model_data.json" "unity\Assets\Data\model_data.json" -Force
Write-Host "Contrato copiado a unity/Assets/Data/model_data.json"