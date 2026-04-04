# vivorgb

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

## Execução

```bash
python3 -m vivorgb probe
python3 -m vivorgb set-color ff5500 --dry-run
python3 -m vivorgb set-brightness 3
python3 -m vivorgb apply --color 00ffaa --brightness 2
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

Exemplo de regra `udev` incluído em `udev/99-vivorgb.rules`.
Para este modelo, a regra usa o nó HID pai `0018:0B05:19B6.0002` e atribui
acesso ao grupo `plugdev`.

## Limitações conhecidas

- A ASUS não publica suporte oficial para esse modelo no Linux.
- O protocolo `19b6` é compatível com muitos notebooks ASUS, mas o `S5406SA`
  ainda não foi validado upstream.
- O ambiente atual não expõe `/dev/hidraw*`, então a validação completa de
  escrita no dispositivo precisa ser feita no host real.
