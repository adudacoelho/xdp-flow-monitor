# IV-D — Classificação

Objetivo: comparar acurácia, precisão, recall, F1 e taxas de detecção de normais
e ataques (Figura 7).

Passo a passo pendente. `make ml` executa apenas o `train_model.py` original,
que treina XGBoost; não faz a comparação de todos os modelos do artigo.
A avaliação adicional foi removida junto com os scripts auxiliares.

Precisamos definir os dados reais, as partições de treino/teste e o contrato de
features antes de apresentar resultados como reprodução do artigo.
