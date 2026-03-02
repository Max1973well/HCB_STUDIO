from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib
import os

# Dados de Treinamento (Exemplos para o Cérebro aprender)
# Podemos expandir esta lista conforme o uso
X_train = [
    "fatura de energia vencimento março", "pagamento efetuado via pix", "nota fiscal de serviço",
    "novo algoritmo de busca em python", "função de criptografia em rust", "erro de compilação no motor",
    "diário de bordo 21 de fevereiro", "lista de compras supermercado", "meu treino de hoje"
]
y_train = ["FINANCEIRO", "FINANCEIRO", "FINANCEIRO", "TECNICO", "TECNICO", "TECNICO", "PESSOAL", "PESSOAL", "PESSOAL"]


def train_brain():
    vectorizer = CountVectorizer()
    # O método correto é fit_transform (apenas um 'fit')
    X = vectorizer.fit_transform(X_train)

    clf = MultinomialNB()
    clf.fit(X, y_train)

    # ... resto do código igual

    # Salvar o cérebro treinado em 00_Core
    model_path = r"F:\HCB_STUDIO\00_Core\engines\brain_v1.pkl"
    vec_path = r"F:\HCB_STUDIO\00_Core\engines\vectorizer_v1.pkl"

    joblib.dump(clf, model_path)
    joblib.dump(vectorizer, vec_path)
    print("--- CÉREBRO TREINADO E ARMAZENADO NO CORE ---")


if __name__ == "__main__":
    train_brain()