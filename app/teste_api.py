import anthropic

client = anthropic.Anthropic()

resp = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "Diga olá em uma frase, em português."}],
)

print(resp.content[0].text)
print("Tokens de entrada:", resp.usage.input_tokens)
print("Tokens de saída:", resp.usage.output_tokens)
