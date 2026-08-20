/*
 * Tradutor PT-BR de NINJA GAIDEN SIGMA (Master Collection)
 * Aplica a traducao do menu na MEMORIA do jogo, DE FORA do processo.
 *
 * Por que de fora: o .exe e lacrado pelo SteamStub e patchear o arquivo da
 * erro 51, entao a traducao tem de ser escrita no processo ja rodando. A
 * saida obvia seria uma dll-proxy dentro do jogo, mas ele fecha sozinho com
 * QUALQUER dll estranha carregada -- ate uma vazia de 12 KB que so devolve
 * TRUE no DllMain. Escrever de fora, com WriteProcessMemory, ele aceita sem
 * reclamar. Foi assim que a traducao foi validada em jogo varias vezes.
 *
 * O arquivo do jogo continua byte a byte identico: nada e gravado em disco.
 *
 * Dois modos de uso:
 *   1) sem argumentos -- espera o jogo aparecer, aplica e sai. Pode abrir
 *      antes ou depois do jogo, tanto faz.
 *   2) com argumentos -- executa o que vier neles e depois aplica. E o modo
 *      para as opcoes de inicializacao da Steam:
 *         "C:\caminho\NG_Tradutor_PTBR.exe" %command%
 *
 * Compilar (w64devkit):
 *   gcc -O2 -s -o NG_Tradutor_PTBR.exe patcher.c -lkernel32 -luser32
 */
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include "patch_dados.h"

#define JOGO        L"NINJA GAIDEN SIGMA.exe"
#define ESPERA_MAX  300      /* segundos esperando o jogo aparecer */
#define MAIOR       512      /* a maior string tem 338 bytes */

/* --------------------------------------------------------- utilitarios */
static DWORD acha_jogo(void)
{
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32W e;
    DWORD pid = 0;
    if (snap == INVALID_HANDLE_VALUE) return 0;
    e.dwSize = sizeof(e);
    if (Process32FirstW(snap, &e)) {
        do {
            if (lstrcmpiW(e.szExeFile, JOGO) == 0) { pid = e.th32ProcessID; break; }
        } while (Process32NextW(snap, &e));
    }
    CloseHandle(snap);
    return pid;
}

/* O snapshot de modulos falha enquanto o processo ainda esta subindo, por
   isso ele e tentado varias vezes ate o modulo principal aparecer. */
static unsigned char *base_do_jogo(DWORD pid)
{
    HANDLE snap;
    MODULEENTRY32W m;
    unsigned char *base = NULL;
    snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snap == INVALID_HANDLE_VALUE) return NULL;
    m.dwSize = sizeof(m);
    if (Module32FirstW(snap, &m)) {
        do {
            if (lstrcmpiW(m.szModule, JOGO) == 0) { base = m.modBaseAddr; break; }
        } while (Module32NextW(snap, &m));
    }
    CloseHandle(snap);
    return base;
}

/* Acha a janela principal do jogo. Serve de sinal de "ja carregou": so
   depois disso a traducao e escrita, para nao mexer na .rdata no meio do
   carregamento. */
static HWND g_janela;
static DWORD g_pid_alvo;

static BOOL CALLBACK ve_janela(HWND h, LPARAM p)
{
    DWORD pid = 0;
    (void)p;
    GetWindowThreadProcessId(h, &pid);
    if (pid == g_pid_alvo && IsWindowVisible(h) && GetWindow(h, GW_OWNER) == NULL) {
        g_janela = h;
        return FALSE;
    }
    return TRUE;
}

static HWND janela_do_jogo(DWORD pid)
{
    g_janela = NULL;
    g_pid_alvo = pid;
    EnumWindows(ve_janela, 0);
    return g_janela;
}

/* -------------------------------------------------------------- patch */
static int aplicar(HANDLE h, unsigned char *base, int *nao_bateram)
{
    unsigned char atual[MAIOR + 1], novo[MAIOR + 1];
    int prontas = 0, i;
    SIZE_T lido, escrito;
    DWORD velho;

    *nao_bateram = 0;
    for (i = 0; i < N_ENTRADAS; i++) {
        const Entrada *e = &ENTRADAS[i];
        unsigned char *p = base + e->rva;
        const unsigned char *es = DADOS + e->off;
        const unsigned char *pt = es + e->nes;
        int quanto = e->nes > e->npt ? e->nes : e->npt;
        int total;

        if (quanto + 1 > MAIOR) { (*nao_bateram)++; continue; }
        if (!ReadProcessMemory(h, p, atual, quanto + 1, &lido) ||
            lido != (SIZE_T)(quanto + 1)) { (*nao_bateram)++; continue; }

        if (memcmp(atual, pt, e->npt) == 0) { prontas++; continue; }  /* ja feita */
        if (memcmp(atual, es, e->nes) != 0) { (*nao_bateram)++; continue; }

        /* Escreve exatamente como o patcher que ja foi validado em jogo: a
           traducao mais os NULs que sobram do campo espanhol. Quando o
           portugues e maior que o espanhol (87 casos), o campo termina no
           preenchimento que ja vinha zerado, entao basta a string. */
        total = e->npt > e->nes ? e->npt : e->nes + 1;
        memcpy(novo, pt, e->npt);
        if (total > e->npt) memset(novo + e->npt, 0, total - e->npt);

        if (!VirtualProtectEx(h, p, total, PAGE_READWRITE, &velho)) {
            (*nao_bateram)++; continue;
        }
        if (WriteProcessMemory(h, p, novo, total, &escrito) &&
            escrito == (SIZE_T)total) prontas++;
        else (*nao_bateram)++;
        VirtualProtectEx(h, p, total, velho, &velho);
    }
    return prontas;
}

/* --------------------------------------------------------------- main */
int main(int argc, char **argv)
{
    DWORD pid = 0;
    HANDLE h;
    unsigned char *base = NULL;
    int prontas, nao_bateram, s;
    (void)argv;   /* a linha de comando e lida inteira por GetCommandLineW */

    SetConsoleOutputCP(65001);
    printf("=================================================\n");
    printf(" NINJA GAIDEN SIGMA -- traducao PT-BR do menu\n");
    printf("=================================================\n\n");

    /* Modo "opcoes de inicializacao da Steam": tudo que veio depois do nome
       deste programa e o comando do jogo, entao e so executar. */
    if (argc > 1) {
        STARTUPINFOW si;
        PROCESS_INFORMATION pi;
        WCHAR *linha = GetCommandLineW();
        WCHAR *p = linha;
        int aspas = 0;
        /* pula o proprio nome para sobrar so o comando do jogo */
        while (*p) {
            if (*p == L'"') aspas = !aspas;
            else if (*p == L' ' && !aspas) break;
            p++;
        }
        while (*p == L' ') p++;
        ZeroMemory(&si, sizeof(si)); si.cb = sizeof(si);
        ZeroMemory(&pi, sizeof(pi));
        printf("Abrindo o jogo...\n");
        if (CreateProcessW(NULL, p, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
        } else {
            printf("Nao consegui abrir o jogo (erro %lu).\n", GetLastError());
        }
    }

    printf("Esperando o jogo...\n");
    for (s = 0; s < ESPERA_MAX * 2 && !pid; s++) {
        pid = acha_jogo();
        if (!pid) Sleep(500);
    }
    if (!pid) {
        printf("\nO jogo nao apareceu em %d segundos.\n", ESPERA_MAX);
        printf("Abra o jogo e rode este programa de novo.\n\n");
        system("pause");
        return 1;
    }
    printf("Jogo encontrado (pid %lu).\n", pid);

    /* Espera a janela aparecer: e o sinal de que a inicializacao acabou.
       Escrever na .rdata no meio do carregamento e pedir encrenca. */
    printf("Esperando a tela do jogo abrir...\n");
    for (s = 0; s < 120 && !janela_do_jogo(pid); s++) Sleep(500);
    Sleep(3000);

    for (s = 0; s < 40 && !base; s++) {
        base = base_do_jogo(pid);
        if (!base) Sleep(500);
    }
    if (!base) {
        printf("\nNao consegui achar o modulo principal do jogo.\n\n");
        system("pause");
        return 1;
    }

    /* SYNCHRONIZE entra na lista porque no modo Steam este programa precisa
       ficar vivo enquanto o jogo estiver aberto -- veja o fim do main(). */
    h = OpenProcess(PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION |
                    PROCESS_QUERY_INFORMATION | SYNCHRONIZE, FALSE, pid);
    if (!h) {
        printf("\nNao consegui abrir o processo (erro %lu).\n", GetLastError());
        printf("Tente rodar este programa como administrador.\n\n");
        system("pause");
        return 1;
    }

    prontas = aplicar(h, base, &nao_bateram);

    printf("\n-------------------------------------------------\n");
    if (prontas >= N_ENTRADAS) {
        printf(" Traducao aplicada: %d de %d textos.\n", prontas, N_ENTRADAS);
        printf(" Pode jogar. Nao precisa deixar esta janela aberta.\n");
    } else if (prontas > 0) {
        printf(" Traducao aplicada em parte: %d de %d textos\n", prontas, N_ENTRADAS);
        printf(" (%d nao bateram -- o jogo pode ter sido atualizado).\n", nao_bateram);
    } else {
        printf(" Nenhum texto foi aplicado.\n");
        printf(" O jogo provavelmente foi atualizado e os enderecos mudaram.\n");
    }
    printf("-------------------------------------------------\n\n");

    if (argc > 1) {
        /* Modo Steam: a Steam considera ESTE programa o jogo, entao sair
           agora faria ela marcar a sessao como encerrada -- sem contagem de
           horas, sem sobreposicao. Ficamos parados ate o jogo fechar. */
        printf(" Esta janela fecha sozinha quando voce sair do jogo.\n\n");
        WaitForSingleObject(h, INFINITE);
        CloseHandle(h);
        return 0;
    }
    CloseHandle(h);
    system("pause");
    return 0;
}
