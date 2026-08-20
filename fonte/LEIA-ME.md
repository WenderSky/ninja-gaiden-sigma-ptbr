# Fonte

O que está aqui é o **como** — as ferramentas que produziram a tradução. Nada disto é necessário para jogar; quem só quer jogar baixa o pacote na aba [Releases](../../releases).

Está publicado por dois motivos: para quem quiser conferir o que os programas fazem antes de rodar, e porque boa parte do caminho foi engenharia reversa que pode servir para outro jogo da mesma casa.

---

## Os dois programas do pacote

| Arquivo | O que é |
|---|---|
| `instalador.c` | Grava os blocos traduzidos no `databin`. C puro, sem zlib: como o índice do arquivo nunca foi alterado, cada bloco volta no mesmo offset e com o mesmo tamanho, então basta escrever bytes no lugar certo. Confere o tamanho do `databin` antes de gravar e desiste se o jogo tiver sido atualizado. |
| `patcher.c` | Escreve o menu na memória do jogo, de fora, com `WriteProcessMemory`. Traz as 918 traduções embutidas (via `patch_dados.h`, gerado por `gen_dados_dll.py`). Espera a janela do jogo aparecer antes de escrever, e só escreve onde encontra exatamente a string espanhola esperada. |

Compilados com [w64devkit](https://github.com/skeeto/w64devkit):

```sh
gcc -O2 -s -o Instalar_Traducao_PTBR.exe instalador.c -lkernel32 -luser32 -lshell32 -municode
gcc -O2 -s -o NG_Tradutor_PTBR.exe patcher.c -lkernel32 -luser32
```

---

## Ferramentas

### O arquivo do jogo

| Arquivo | O que faz |
|---|---|
| `dbx.py` | Leitor do `databin`. Índice de 32 bytes por registro a partir de `0x13180`, dados zlib a partir de `0x4601c`. É a base de quase tudo aqui. |
| `blocos_mudados.py` | Descobre quais blocos a tradução alterou, cruzando três fontes independentes (backup do instalador antigo, backups locais e uma varredura atrás de marcas de português). |
| `gerar_pacote.py` | Monta o `NG_PTBR.dados` a partir do `databin` já traduzido. |
| `conferir_pacote.py` | Confere o pacote gerado contra o `databin`, byte a byte. |

### A fonte e a acentuação

| Arquivo | O que faz |
|---|---|
| `g1t.py` | Leitor das texturas GT1G/G1T. As que interessam são formato `0x01`, RGBA8 cru — editáveis no lugar. |
| `mk_til.py` | Redesenha `ä ö Ä Ö` do atlas como `ã õ Ã Õ`. A charmap está no executável cifrado, então não dá para criar caractere novo: a saída foi repintar glifos que o português não usa. |
| `mk_ordinal.py` | Monta `º` e `ª` a partir do `o` e do `a` reduzidos a 56%, alinhados pelo topo dos números. |
| `gen_fonte.py` / `aplicar_fonte.py` | Geram e aplicam o bloco da fonte (`02771`). |
| `texto_sub.py` | A regra de substituição, num lugar só: `ã→ä`, `õ→ö`, `Ã→Ä`, `Õ→Ö`, `º→ý`, `ª→ÿ`. |

### O menu, que é imagem

| Arquivo | O que faz |
|---|---|
| `banner.py` | Recorta as faixas de menu letra por letra, achando os limites pela coluna de menor tinta. |
| `compor.py` | Remonta a frase em português com o espaçamento medido da original e recalcula o brilho a partir dela. |
| `diacritico.py` | Extrai til, cedilha e circunflexo da fonte serifada do jogo para montar letras acentuadas que não existiam nas faixas. |
| `menu_gen.py` / `titulo_gen.py` | Geram as faixas do menu e a tela de título. |
| `aplicar_menu.py` | Grava as texturas de volta no `databin`. |

### O executável

| Arquivo | O que faz |
|---|---|
| `gen_dados_dll.py` | Transforma a tabela de traduções num cabeçalho C para embutir no patcher. Guarda o texto espanhol junto do português de propósito: o patcher confere antes de escrever, então se o jogo for atualizado ele simplesmente não faz nada. |

---

## O caminho que não deu certo

Houve uma tentativa de fazer isto virar um mod que carrega sozinho — uma DLL-proxy na pasta do jogo (`dinput8.dll`, depois `dbghelp.dll`). **Não funciona, e vale registrar para ninguém perder tempo repetindo.**

O jogo fecha sozinho, em cerca de um segundo, se **qualquer** DLL estranha for carregada no processo. Não é o que a DLL faz: uma DLL vazia de 12 KB, sem thread, sem escrever em disco, sem tocar em memória, só com um `DllMain` que devolve `TRUE`, derruba o jogo do mesmo jeito. Ele sai limpo, com `ExitProcess`, sem exceção e sem nada no Visualizador de Eventos do Windows — é uma verificação deliberada, não uma falha.

O diagnóstico levou algumas rodadas porque as pistas apontavam para o lado errado: o log da DLL registrava `918 de 918 strings` aplicadas com sucesso antes de o jogo morrer, o que fazia parecer problema do patch. Só um teste com a escrita adiada para 30 segundos — em que o jogo morreu **antes** de escrever qualquer coisa — descartou essa hipótese.

Escrever de fora, com o jogo já aberto, ele aceita sem reclamar. Daí o tradutor ser um programa separado.
