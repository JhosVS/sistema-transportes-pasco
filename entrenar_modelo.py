# entrenar_modelo.py
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error

def entrenar_modelo():
    print("--- 1. Cargando el conjunto de datos desde CSV ---")
    df = pd.read_csv('dataset_demanda.csv')
    print(f"Total de registros de viajes procesados: {len(df)}")

    # 2. Definir las variables explicativas (X) y el objetivo (y)
    columnas_features = [
        'dia_semana_num', 
        'mes', 
        'dia_mes', 
        'es_fin_semana', 
        'id_ruta', 
        'id_sede_origen', 
        'id_sede_destino', 
        'hora_salida_decimal', 
        'precio_pasaje_base', 
        'capacidad_asientos'
    ]
    
    X = df[columnas_features]
    y = df['pasajes_vendidos']

    # 3. Separar datos: 80% para entrenar y 20% para evaluar (examen final)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("--- 2. Entrenando Random Forest Regressor ---")
    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
    modelo.fit(X_train, y_train)

    # 4. Probar la precisión del modelo con el 20% de prueba
    predicciones = modelo.predict(X_test)
    
    mae = mean_absolute_error(y_test, predicciones)
    rmse = mean_squared_error(y_test, predicciones) ** 0.5
    r2 = r2_score(y_test, predicciones)

    print("\n================ EVALUACIÓN DEL MODELO ================")
    print(f"📊 Error Absoluto Medio (MAE): {mae:.2f} pasajes")
    print(f"📊 Raíz del Error Cuadrático (RMSE): {rmse:.2f} pasajes")
    print(f"🎯 Precisión / Coeficiente R²: {r2 * 100:.2f}%")
    print("========================================================\n")

    # 5. Guardar el modelo entrenado en disco (.joblib)
    joblib.dump(modelo, 'modelo_demanda.joblib')
    print("💾 ¡Éxito! El modelo ha sido empaquetado y guardado como 'modelo_demanda.joblib'.")

if __name__ == "__main__":
    entrenar_modelo()