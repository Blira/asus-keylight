# asus-keylight

CLI experimental para controlar o RGB do teclado do ASUS Vivobook S 14 `S5406SA`
no Linux.

O projeto detecta:

- o modelo da máquina via DMI;
- o controlador HID `0B05:19B6`;
- o backlight padrão exposto em `/sys/class/leds/asus::kbd_backlight`.
- suporte HID Lighting/LampArray no `report_descriptor`, quando disponível.

Na implementação atual, a CLI:

- prefere o protocolo HID Lighting/LampArray quando o teclado o anuncia;
- usa o fallback antigo de pacotes ASUS `0x5D B3/B4/B5` quando o LampArray não existe.

Os comandos suportados são:

- `probe`
- `set-color RRGGBB`
- `set-brightness 0|1|2|3`
- `apply --color RRGGBB --brightness N`
- `asus-keylight-gui` para abrir a interface gráfica

## Execução

```bash
python3 -m asus_keylight probe
python3 -m asus_keylight set-color ff5500 --dry-run
python3 -m asus_keylight set-brightness 3
python3 -m asus_keylight apply --color 00ffaa --brightness 2
```

## App gráfica

A interface gráfica usa `tkinter`, então não adiciona dependências Python
extras na maioria das distribuições.

Instalação mais simples a partir de um clone:

```bash
./install.sh
```

Depois de instalar o projeto, você pode abrir a app com:

```bash
asus-keylight-gui
```

Para adicionar ao menu de aplicativos:

```bash
asus-keylight-install-desktop
```

Ou sem instalar scripts:

```bash
python3 -m asus_keylight.gui
```

Recursos da app:

- seletor visual de cor;
- presets prontos;
- ajuste de brilho 0..3;
- botão para aplicar só a cor ou cor + brilho;
- preview maior com destaque da cor atual;
- feedback de erro/status na própria janela.

Instalação manual sem `install.sh`:

```bash
sudo apt install python3-tk
python3 -m asus_keylight.install_desktop
```

Se `~/.local/bin` não estiver no seu `PATH`, execute diretamente:

```bash
python3 -m asus_keylight.gui
```

## Dependências

Nenhuma dependência externa é obrigatória.

Se `python3-hid` ou `python3-hidapi` estiverem instalados, a CLI tenta usar
`hidapi` primeiro. Caso contrário, usa `hidraw` com `ioctl` diretamente.

## Permissões

Para gravar no teclado RGB, você provavelmente precisará:

- executar com `sudo`, ou
- instalar uma regra `udev` para permitir acesso ao `hidraw` correspondente.

O ajuste de brilho usa o sysfs padrão do ASUS e também pode exigir privilégios.

Exemplo de regra `udev` incluído em `udev/99-asus-keylight.rules`.
Para este modelo, a regra usa o nó HID pai `0018:0B05:19B6.0002` e atribui
acesso ao grupo `plugdev`.

## Limitações conhecidas

- A ASUS não publica suporte oficial para esse modelo no Linux.
- O protocolo `19b6` é compatível com muitos notebooks ASUS, mas o `S5406SA`
  ainda não foi validado upstream.
- O ambiente atual não expõe `/dev/hidraw*`, então a validação completa de
  escrita no dispositivo precisa ser feita no host real.
