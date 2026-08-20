/*
 * Instalador da traducao PT-BR -- NINJA GAIDEN SIGMA (Master Collection)
 *
 * Grava no databin os blocos ja traduzidos que vem no NG_PTBR.dados. Como a
 * traducao nunca mexeu no indice do arquivo, cada bloco volta exatamente no
 * mesmo offset e com o mesmo tamanho do original -- por isso aqui nao ha
 * zlib nem recomposicao: e so gravar bytes no lugar certo.
 *
 * Antes de escrever qualquer coisa ele confere o tamanho do databin contra o
 * carimbo do pacote. Se a Steam atualizar o jogo, os offsets mudam, o
 * carimbo nao bate e o programa desiste em vez de estragar 2,3 GB.
 *
 * Compilar (w64devkit):
 *   gcc -O2 -s -o Instalar_Traducao_PTBR.exe instalador.c -lkernel32 -luser32 -lshell32
 */
#include <windows.h>
#include <stdio.h>

#define MAGIC       "NGPTBR03"
#define DADOS       L"NG_PTBR.dados"
#define SUFIXO_BK   L".ptbr_backup_v3"

static WCHAR g_databin[MAX_PATH];
static WCHAR g_pasta[MAX_PATH];

/* ------------------------------------------------------------ procura */
/* Varre os lugares onde a Steam costuma instalar. O nome da pasta do jogo
   tem um sigma no fim, entao a busca e por curinga em vez de nome fixo. */
static const WCHAR *RAIZES[] = {
    L"%c:\\SteamLibrary\\steamapps\\common\\",
    L"%c:\\Program Files (x86)\\Steam\\steamapps\\common\\",
    L"%c:\\Program Files\\Steam\\steamapps\\common\\",
    L"%c:\\Steam\\steamapps\\common\\",
    L"%c:\\Games\\Steam\\steamapps\\common\\",
    NULL
};

static BOOL existe(const WCHAR *p)
{
    DWORD a = GetFileAttributesW(p);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static BOOL procura_databin(void)
{
    WCHAR raiz[MAX_PATH], busca[MAX_PATH], teste[MAX_PATH];
    WIN32_FIND_DATAW fd;
    HANDLE h;
    int r;
    WCHAR letra;

    for (letra = L'C'; letra <= L'J'; letra++) {
        for (r = 0; RAIZES[r]; r++) {
            wsprintfW(raiz, RAIZES[r], letra);
            wsprintfW(busca, L"%s*NINJA*GAIDEN*", raiz);
            h = FindFirstFileW(busca, &fd);
            if (h == INVALID_HANDLE_VALUE) continue;
            do {
                if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) continue;
                wsprintfW(teste, L"%s%s\\databin\\databin", raiz, fd.cFileName);
                if (existe(teste)) {
                    lstrcpyW(g_databin, teste);
                    FindClose(h);
                    return TRUE;
                }
            } while (FindNextFileW(h, &fd));
            FindClose(h);
        }
    }
    return FALSE;
}

/* -------------------------------------------------------------- dados */
/* O cabecalho de cada bloco vai EMPACOTADO no arquivo: 4 + 8 + 4 = 16 bytes.
   Uma struct em C teria 24 por causa do alinhamento do campo de 64 bits, e
   ler direto por cima dela desalinharia tudo a partir do primeiro bloco --
   por isso os campos sao lidos e gravados um a um. */
typedef struct { unsigned int num; unsigned __int64 off; unsigned int comp; } Cab;
#define CAB_BYTES 16

static BOOL le_cab(HANDLE h, Cab *c)
{
    unsigned char b[CAB_BYTES];
    DWORD lido;
    if (!ReadFile(h, b, CAB_BYTES, &lido, NULL) || lido != CAB_BYTES) return FALSE;
    memcpy(&c->num, b, 4);
    memcpy(&c->off, b + 4, 8);
    memcpy(&c->comp, b + 12, 4);
    return TRUE;
}

static BOOL grava_cab(HANDLE h, const Cab *c)
{
    unsigned char b[CAB_BYTES];
    DWORD escrito;
    memcpy(b, &c->num, 4);
    memcpy(b + 4, &c->off, 8);
    memcpy(b + 12, &c->comp, 4);
    return WriteFile(h, b, CAB_BYTES, &escrito, NULL) && escrito == CAB_BYTES;
}

/* Caminho largo -> UTF-8, para nao misturar printf com wprintf no mesmo
   fluxo (misturar os dois deixa o stream numa orientacao so e come a saida). */
static void mostra_caminho(const WCHAR *w)
{
    char curto[MAX_PATH * 3];
    WideCharToMultiByte(CP_UTF8, 0, w, -1, curto, sizeof(curto), NULL, NULL);
    printf("%s\n", curto);
}

static HANDLE abre_dados(unsigned __int64 *tam_ref, unsigned int *n_blocos)
{
    WCHAR caminho[MAX_PATH];
    HANDLE h;
    char magic[8];
    unsigned int versao;
    DWORD lido;

    lstrcpyW(caminho, g_pasta);
    lstrcatW(caminho, L"\\" DADOS);
    h = CreateFileW(caminho, GENERIC_READ, FILE_SHARE_READ, NULL,
                    OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        printf("ERRO: nao achei o arquivo NG_PTBR.dados ao lado deste programa.\n");
        printf("      Mantenha os dois na mesma pasta.\n");
        return INVALID_HANDLE_VALUE;
    }
    ReadFile(h, magic, 8, &lido, NULL);
    if (lido != 8 || memcmp(magic, MAGIC, 8) != 0) {
        printf("ERRO: NG_PTBR.dados esta corrompido.\n");
        CloseHandle(h);
        return INVALID_HANDLE_VALUE;
    }
    ReadFile(h, &versao, 4, &lido, NULL);
    ReadFile(h, tam_ref, 8, &lido, NULL);
    ReadFile(h, n_blocos, 4, &lido, NULL);
    return h;
}

static unsigned __int64 tamanho_de(HANDLE h)
{
    LARGE_INTEGER li;
    if (!GetFileSizeEx(h, &li)) return 0;
    return (unsigned __int64)li.QuadPart;
}

static BOOL posiciona(HANDLE h, unsigned __int64 off)
{
    LARGE_INTEGER li;
    li.QuadPart = (LONGLONG)off;
    return SetFilePointerEx(h, li, NULL, FILE_BEGIN);
}

/* Compara o primeiro bloco do pacote com o que esta no databin. Serve so
   para saber se a traducao ja foi instalada; depois o ponteiro de leitura
   volta para logo depois do cabecalho. */
#define INICIO_DOS_BLOCOS 24

static BOOL ja_traduzido(HANDLE db, HANDLE dados)
{
    Cab c;
    unsigned char *pacote, *atual;
    DWORD lido;
    BOOL igual = FALSE;

    posiciona(dados, INICIO_DOS_BLOCOS);
    if (!le_cab(dados, &c)) return FALSE;
    pacote = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, c.comp);
    atual = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, c.comp);
    if (pacote && atual &&
        ReadFile(dados, pacote, c.comp, &lido, NULL) && lido == c.comp) {
        posiciona(db, c.off);
        if (ReadFile(db, atual, c.comp, &lido, NULL) && lido == c.comp)
            igual = (memcmp(pacote, atual, c.comp) == 0);
    }
    if (pacote) HeapFree(GetProcessHeap(), 0, pacote);
    if (atual) HeapFree(GetProcessHeap(), 0, atual);
    posiciona(dados, INICIO_DOS_BLOCOS);
    return igual;
}

/* ----------------------------------------------------------- instalar */
static int instalar(HANDLE db, HANDLE dados, unsigned int n_blocos)
{
    WCHAR cbk[MAX_PATH];
    HANDLE bk = INVALID_HANDLE_VALUE;
    unsigned char *buf, *orig;
    unsigned int i, gravados = 0;
    DWORD lido, escrito;
    Cab c;
    BOOL fazer_backup, tinha_backup;

    lstrcpyW(cbk, g_databin);
    lstrcatW(cbk, SUFIXO_BK);
    tinha_backup = (GetFileAttributesW(cbk) != INVALID_FILE_ATTRIBUTES);
    fazer_backup = !tinha_backup;

    /* Se o databin ja estiver traduzido, um "backup" guardaria a traducao em
       vez do original -- e o Reverter nao reverteria nada. Melhor nao criar
       e dizer isso na cara do usuario. */
    if (fazer_backup && ja_traduzido(db, dados)) {
        printf("Este databin JA esta traduzido.\n");
        printf("Nao vou criar backup (ele guardaria a traducao, nao o original).\n");
        printf("Para voltar ao original: Steam > botao direito no jogo >\n");
        printf("Propriedades > Arquivos locais > Verificar integridade.\n\n");
        fazer_backup = FALSE;
    }
    if (fazer_backup) {
        bk = CreateFileW(cbk, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                         FILE_ATTRIBUTE_NORMAL, NULL);
        if (bk == INVALID_HANDLE_VALUE) {
            printf("AVISO: nao consegui criar o backup. Seguindo sem ele.\n");
            fazer_backup = FALSE;
        } else {
            WriteFile(bk, MAGIC, 8, &escrito, NULL);
            WriteFile(bk, &n_blocos, 4, &escrito, NULL);
        }
    } else if (tinha_backup) {
        printf("Backup ja existe, mantendo o original de antes.\n");
    }

    printf("\nGravando %u blocos:\n", n_blocos);
    for (i = 0; i < n_blocos; i++) {
        if (!le_cab(dados, &c)) {
            printf("\nERRO: NG_PTBR.dados terminou antes da hora.\n");
            break;
        }
        buf = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, c.comp);
        if (!buf) break;
        if (!ReadFile(dados, buf, c.comp, &lido, NULL) || lido != c.comp) {
            HeapFree(GetProcessHeap(), 0, buf);
            printf("\nERRO: leitura do bloco %u falhou.\n", c.num);
            break;
        }

        if (fazer_backup) {
            orig = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, c.comp);
            if (orig) {
                posiciona(db, c.off);
                if (ReadFile(db, orig, c.comp, &lido, NULL) && lido == c.comp) {
                    grava_cab(bk, &c);
                    WriteFile(bk, orig, c.comp, &escrito, NULL);
                }
                HeapFree(GetProcessHeap(), 0, orig);
            }
        }

        posiciona(db, c.off);
        if (WriteFile(db, buf, c.comp, &escrito, NULL) && escrito == c.comp)
            gravados++;
        HeapFree(GetProcessHeap(), 0, buf);

        if ((i % 20) == 0) { printf("."); fflush(stdout); }
    }
    if (bk != INVALID_HANDLE_VALUE) CloseHandle(bk);
    FlushFileBuffers(db);
    printf("\n");
    return (int)gravados;
}

/* ----------------------------------------------------------- reverter */
static int reverter(HANDLE db)
{
    WCHAR cbk[MAX_PATH];
    HANDLE bk;
    char magic[8];
    unsigned int n, i, voltados = 0;
    DWORD lido, escrito;
    Cab c;
    unsigned char *buf;

    lstrcpyW(cbk, g_databin);
    lstrcatW(cbk, SUFIXO_BK);
    bk = CreateFileW(cbk, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
                     FILE_ATTRIBUTE_NORMAL, NULL);
    if (bk == INVALID_HANDLE_VALUE) {
        printf("\nNao ha backup para reverter.\n");
        printf("Use 'Verificar integridade dos arquivos' na Steam: ela\n");
        printf("baixa o databin original de volta.\n");
        return 0;
    }
    ReadFile(bk, magic, 8, &lido, NULL);
    if (lido != 8 || memcmp(magic, MAGIC, 8) != 0) {
        printf("\nBackup invalido.\n");
        CloseHandle(bk);
        return 0;
    }
    ReadFile(bk, &n, 4, &lido, NULL);
    printf("\nRestaurando %u blocos:\n", n);
    for (i = 0; i < n; i++) {
        if (!le_cab(bk, &c)) break;
        buf = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, c.comp);
        if (!buf) break;
        if (ReadFile(bk, buf, c.comp, &lido, NULL) && lido == c.comp) {
            posiciona(db, c.off);
            if (WriteFile(db, buf, c.comp, &escrito, NULL) && escrito == c.comp)
                voltados++;
        }
        HeapFree(GetProcessHeap(), 0, buf);
        if ((i % 20) == 0) { printf("."); fflush(stdout); }
    }
    CloseHandle(bk);
    FlushFileBuffers(db);
    printf("\n");
    return (int)voltados;
}

/* --------------------------------------------------------------- main */
int wmain(int argc, WCHAR **argv)
{
    HANDLE db, dados;
    unsigned __int64 tam_ref, tam_real;
    unsigned int n_blocos;
    int op, feitos;
    char linha[16];

    SetConsoleOutputCP(65001);
    printf("============================================================\n");
    printf("  TRADUCAO PT-BR  --  NINJA GAIDEN SIGMA (Master Collection)\n");
    printf("============================================================\n\n");

    GetModuleFileNameW(NULL, g_pasta, MAX_PATH);
    {
        WCHAR *p = g_pasta, *ult = NULL;
        while (*p) { if (*p == L'\\') ult = p; p++; }
        if (ult) *ult = 0;
    }

    dados = abre_dados(&tam_ref, &n_blocos);
    if (dados == INVALID_HANDLE_VALUE) { system("pause"); return 1; }

    if (argc > 1) lstrcpyW(g_databin, argv[1]);
    else if (!procura_databin()) {
        printf("Nao achei o jogo automaticamente.\n\n");
        printf("Arraste o arquivo 'databin' (fica na pasta do jogo, dentro\n");
        printf("da pasta 'databin') para cima deste programa.\n\n");
        CloseHandle(dados);
        system("pause");
        return 1;
    }
    printf("Jogo encontrado em:\n  ");
    mostra_caminho(g_databin);
    printf("\n");

    db = CreateFileW(g_databin, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                     OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (db == INVALID_HANDLE_VALUE) {
        printf("Nao consegui abrir o databin (erro %lu).\n", GetLastError());
        printf("Feche o jogo e a Steam e tente de novo.\n\n");
        CloseHandle(dados);
        system("pause");
        return 1;
    }

    tam_real = tamanho_de(db);
    if (tam_real != tam_ref) {
        printf("O databin deste computador tem tamanho diferente do esperado:\n");
        printf("  esperado: %llu bytes\n  aqui    : %llu bytes\n\n", tam_ref, tam_real);
        printf("Isso quer dizer que o jogo foi atualizado depois desta traducao.\n");
        printf("Nao vou gravar nada para nao estragar o arquivo.\n\n");
        CloseHandle(db);
        CloseHandle(dados);
        system("pause");
        return 1;
    }

    printf("Escolha:\n");
    printf("  [1] Instalar a traducao\n");
    printf("  [2] Reverter (voltar ao original)\n");
    printf("  [3] Sair\n> ");
    if (!fgets(linha, sizeof(linha), stdin)) linha[0] = '3';
    op = linha[0];

    if (op == '1') {
        feitos = instalar(db, dados, n_blocos);
        printf("\n------------------------------------------------------------\n");
        if (feitos == (int)n_blocos) {
            printf(" Traducao instalada: %d de %u blocos.\n", feitos, n_blocos);
            printf("\n IMPORTANTE: no jogo, deixe o idioma em ESPANHOL.\n");
            printf(" E rode o NG_Tradutor_PTBR.exe para traduzir o menu.\n");
        } else {
            printf(" Gravados %d de %u blocos. Algo deu errado.\n", feitos, n_blocos);
            printf(" Use a opcao [2] para reverter.\n");
        }
        printf("------------------------------------------------------------\n\n");
    } else if (op == '2') {
        feitos = reverter(db);
        if (feitos) printf("\n Revertido: %d blocos voltaram ao original.\n\n", feitos);
    } else {
        printf("\nSaindo.\n\n");
    }

    CloseHandle(db);
    CloseHandle(dados);
    system("pause");
    return 0;
}
