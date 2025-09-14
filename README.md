# JurisData

[![Licença](https://img.shields.io/github/license/MayronDAV/JurisData.svg)](https://github.com/MayronDAV/JurisData/blob/master/LICENSE)

No momento o código só foi testado no Windows.

---

## 📥 Instalação

### Clone o Repositório

```bash
git clone https://github.com/MayronDAV/JurisData
```

### Instale as dependências

```bash
pip install -e .
```

### Compile o Servidor (Opcional)

```bash
.\BuildServer.bat
```

ou

```bash
python Scripts/Compiler.py --batch Server/batch_config.json
```

### Compile o Cliente

```bash
mkdir build
cmake -S Client -B build
```

---

## 🤝 Contribuindo

1. Faça um fork do projeto

2. Crie seu branch da funcionalidade (git checkout -b feature/AmazingFeature)

3. Faça o commit das suas alterações (git commit -m 'Added some amazing feature')

4. Faça o push para o branch (git push origin feature/AmazingFeature)

5. Abra um Pull Request

---

### 📜 Licença

Distribuído sob a [Licença Apache 2.0](https://github.com/MayronDAV/JurisData/blob/master/LICENSE). Consulte **LICENSE** para obter mais informações.
