import argparse
import time

from sentinel_core import sort_files as core_sort_files
from sentinel_smart import smart_sort_v3


def parse_args():
    parser = argparse.ArgumentParser(
        description="HCB Sentinel - Orquestrador de Triagem"
    )
    parser.add_argument(
        "--mode",
        choices=["core", "smart"],
        default="smart",
        help="Modo de operação: core (por extensão) ou smart (IA)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Intervalo entre ciclos em segundos (padrão: 2.0)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas um ciclo de triagem e encerra",
    )
    return parser.parse_args()


def run_cycle(mode):
    if mode == "core":
        core_sort_files()
    else:
        smart_sort_v3()


def main():
    args = parse_args()

    print("--- HCB SENTINEL ORCHESTRATOR ---")
    print(f"Modo: {args.mode.upper()} | Intervalo: {args.interval}s")
    print("Pressione Ctrl+C para encerrar.\n")

    try:
        if args.once:
            run_cycle(args.mode)
            print("Ciclo único concluído.")
            return

        while True:
            run_cycle(args.mode)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n--- TURNO ENCERRADO ---")


if __name__ == "__main__":
    main()
