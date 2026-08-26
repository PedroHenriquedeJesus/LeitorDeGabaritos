# CorretorApp

Aplicação web para criar provas objetivas, gerar cartões-resposta, corrigir arquivos digitalizados e acompanhar notas por turma.

## Recursos

- painel com indicadores de alunos, turmas, provas e correções;
- cadastro, edição e exclusão de alunos e turmas;
- importação de alunos por CSV;
- criação de provas com gabarito, pesos e até sete alternativas;
- atribuição da mesma prova a uma ou mais turmas;
- geração de cartões-resposta em PDF com QR Code e cabeçalho profissional;
- correção de imagens digitalizadas ou arquivos CSV;
- lançamento, edição e exclusão manual de notas;
- exportação das notas da turma em CSV.
- acesso autenticado e troca de senha pelo administrador.

## Arquitetura

```text
CorretorApp/
├── backend/              API FastAPI, regras de negócio e banco SQLite
│   ├── app/api/          endpoints HTTP
│   ├── app/models/       modelos SQLAlchemy
│   ├── app/schemas/      contratos Pydantic
│   └── app/services/     inicialização e geração de cartões-resposta
├── frontend/             aplicação React + TypeScript construída com Vite
└── src/
    ├── assets/           imagem usada no QR Code
    └── test_core/        motor de geração e leitura dos cartões-resposta
```

O frontend consome a API pelo prefixo `/api`. Durante o desenvolvimento, o Vite encaminha essas chamadas para `http://localhost:8000`.

O motor em `src/test_core/` é executado pelo backend em processos separados. Por isso, essa pasta e `src/assets/logo_qr_corretorapp.png` fazem parte do runtime e não devem ser removidas.

## Requisitos

- Python 3.10;
- Node.js e npm;
- biblioteca nativa do ZBar, exigida pelo `pyzbar` para ler QR Codes.

No Windows, a DLL do ZBar normalmente é instalada junto com o pacote Python. Em distribuições Linux, instale o pacote fornecido pelo sistema, como `libzbar0` em Debian/Ubuntu.

## Execução local

### 1. Backend

No PowerShell, a partir da raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
# Edite backend\.env e defina o administrador inicial antes do primeiro uso.
Set-Location backend
python -m uvicorn app.main:app --reload
```

No Linux ou macOS, troque a ativação do ambiente por:

```bash
source .venv/bin/activate
```

A API ficará disponível em `http://127.0.0.1:8000` e a documentação interativa em `http://127.0.0.1:8000/docs`.

### 2. Frontend

Em outro terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

A interface ficará disponível em `http://127.0.0.1:5173`.

## Configuração

As configurações do backend são lidas de `backend/.env`. Use `backend/.env.example` como base:

> O arquivo `backend/.env` é local e pode conter credenciais. Nunca o envie ao GitHub. Versione somente o modelo `backend/.env.example`, mantendo os campos de usuário e senha inicial vazios.

```dotenv
APP_NAME=CorretorApp
DATABASE_URL=sqlite:///./corretorapp.db
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
INITIAL_ADMIN_USERNAME=master_user
INITIAL_ADMIN_PASSWORD=12345678
AUTH_SESSION_HOURS=12
```

Variáveis:

- `APP_NAME`: nome exibido pela API;
- `DATABASE_URL`: conexão SQLAlchemy; por padrão, usa `backend/corretorapp.db`;
- `CORS_ORIGINS`: origens autorizadas a acessar a API.
- `INITIAL_ADMIN_USERNAME`: usuário criado somente quando o banco ainda não possui usuários;
- `INITIAL_ADMIN_PASSWORD`: senha usada somente na criação do primeiro administrador;
- `AUTH_SESSION_HOURS`: duração, em horas, de uma sessão autenticada.

Ao iniciar, o backend cria as tabelas ausentes. Se o banco ainda não tiver usuários, as duas variáveis do administrador inicial são obrigatórias. Depois da criação, elas não alteram a conta existente e podem ser removidas do arquivo `.env`.

## Primeiro acesso e segurança

Para uma instalação nova em ambiente local controlado, as credenciais padrão são:

- usuário: `master_user`;
- senha: `12345678`.

Essas credenciais não ficam embutidas no código. Antes da primeira execução, copie `backend/.env.example` para `backend/.env` e configure nele:

```dotenv
INITIAL_ADMIN_USERNAME=master_user
INITIAL_ADMIN_PASSWORD=12345678
```

O backend usa esses valores somente quando o banco ainda não possui usuários. Se o banco já contiver um administrador, alterar o `.env` não redefine sua senha.

Na primeira inicialização, somente a conta administrativa é criada. Alunos, turmas e provas começam vazios e devem ser cadastrados pelo usuário.

Esses valores são públicos e não devem permanecer em uma instalação acessível por outras pessoas ou pela internet. Após entrar pela primeira vez, abra **Controle de usuários**, selecione **Trocar senha** e defina uma senha exclusiva. A alteração encerra todas as sessões abertas e exige um novo login.

As sessões usam tokens aleatórios. Apenas o hash de cada token e o hash bcrypt da senha são armazenados no banco. O arquivo SQLite existente contém dados locais; faça uma cópia antes de substituí-lo ou removê-lo.

## Guia de uso do aplicativo

O fluxo recomendado é cadastrar os alunos e as turmas, criar uma prova, atribuí-la às turmas, imprimir os cartões-resposta e, depois da aplicação, enviar as imagens para correção.

### 1. Entrar no sistema

1. Com o backend e o frontend em execução, acesse `http://127.0.0.1:5173`.
2. Informe o usuário e a senha definidos na configuração inicial.
3. No primeiro acesso, troque a senha padrão em **Controle de usuários**.

Use o botão de saída no canto superior direito para encerrar a sessão. Se a sessão expirar, o aplicativo solicitará um novo login.

### 2. Cadastrar alunos e turmas

Abra **Alunos e turmas** no menu lateral.

- Para cadastrar um aluno manualmente, preencha o nome e, se disponíveis, o e-mail, a matrícula e a turma. Depois, selecione **Cadastrar aluno**.
- Para criar ou consultar turmas, selecione **Turmas** no topo da página. Informe o nome da turma, o curso e marque os alunos que farão parte dela.
- Use os botões de lápis e lixeira nas tabelas para editar ou excluir registros.

Também é possível importar alunos por CSV. O arquivo pode usar vírgula ou ponto e vírgula como separador e deve conter as colunas `nome`, `turma` e `matricula`:

```csv
nome;turma;matricula
Ana Beatriz;8º Ano A;2026001
Carlos Eduardo;8º Ano A;2026002
```

Durante a importação, turmas ainda inexistentes são criadas automaticamente. Confira os alunos e os vínculos antes de prosseguir.

### 3. Criar uma prova

Abra **Provas** e preencha:

- nome e descrição da prova;
- quantidade de questões;
- quantidade de alternativas, entre duas e sete;
- alternativa correta de cada questão.

Selecione **Salvar prova**. Uma prova existente pode ser alterada pelo botão de edição, mas a mudança do gabarito afeta as correções realizadas posteriormente.

### 4. Atribuir a prova e gerar os cartões-resposta

Na própria página **Provas**:

1. Escolha a prova em **Atribuir prova a turmas**.
2. Marque uma ou mais turmas e selecione **Atribuir prova**.
3. Em **Turmas atribuídas**, localize a combinação de prova e turma.
4. Selecione **PDF** para baixar os cartões-resposta de todos os alunos daquela turma.

Cada cartão contém a identificação do aluno e um QR Code próprio. Não reutilize o cartão de outro aluno nem altere o QR Code.

### 5. Imprimir e preencher

- Imprima o PDF sem cortar ou redimensionar o conteúdo da página.
- Use caneta azul ou preta.
- Marque somente uma alternativa por questão e preencha o círculo completamente.
- Não risque o QR Code, os quadrados de referência ou os marcadores triangulares nos cantos.

### 6. Corrigir os cartões

Digitalize ou fotografe cada página preenchida. Para melhorar a leitura, mantenha a folha plana, com boa iluminação, sem desfoque e com todos os marcadores visíveis.

Depois, abra **Correção**:

1. Selecione a atribuição correspondente à prova e à turma.
2. Em **Escolher arquivos**, selecione uma ou mais imagens dos cartões digitalizados.
3. Selecione **Corrigir arquivos**.
4. Confira o aluno, a matrícula, a nota e o nome do arquivo na lista de resultados.

O envio aceita imagens e arquivos CSV; o envio direto de PDF não é suportado. Para correção por CSV, use uma coluna `matricula` e uma coluna para cada questão (`q1`, `q2`, `q3` etc.). As respostas podem ser letras de `A` a `G` ou números de `1` a `7`:

```csv
matricula;q1;q2;q3;q4;q5
2026001;A;C;B;D;A
2026002;1;3;2;4;1
```

### 7. Consultar e ajustar notas

Abra **Notas** e escolha a turma e a prova. Nessa página é possível:

- consultar as notas já corrigidas;
- corrigir a imagem de um único aluno;
- lançar uma nota manualmente;
- editar ou excluir uma nota existente;
- selecionar **Gerar relatório** para baixar as notas em CSV.

Sempre confira a origem da nota e os resultados antes de distribuir o relatório.

### 8. Alterar a senha administrativa

Abra **Controle de usuários**, informe a senha atual e uma nova senha com pelo menos oito caracteres. Confirme a alteração em **Alterar senha**.

A troca encerra todas as sessões abertas. Entre novamente usando a nova senha.

### Cuidados com exclusões

As exclusões podem remover vínculos e resultados relacionados. Em especial, excluir uma prova também exclui suas atribuições e correções, enquanto **Excluir todos** na página de alunos remove vínculos com turmas e resultados desses estudantes. Faça uma cópia do banco antes de operações em massa.

## Comandos úteis

```powershell
# Gerar o frontend de produção
Set-Location frontend
npm run build

# Verificar a sintaxe do backend e do motor de correção
Set-Location ..
python -m compileall -q backend\app src\test_core
```

Os artefatos `frontend/node_modules/`, `frontend/dist/`, ambientes virtuais, caches Python e caches de cartões-resposta são gerados localmente e não fazem parte do código-fonte.

## Formato do CSV de correção

O CSV deve conter uma coluna `matricula` e colunas `q1`, `q2`, `q3` e assim por diante. As respostas aceitam letras de `A` a `G` ou números de `1` a `7`.
