# Objetivo do script:
# Fornecer utilitarios de execucao protegida para garantir teardown explicito de recursos externos usados pela integracao.
# Processo:
# 1. Classe RuntimeCleanup registra callbacks de limpeza em ordem LIFO.
# 2. register() adiciona callback generico; register_process() adiciona cleanup de subprocesso.
# 3. managed_execution() cria contexto gerenciado que:
#    a. Registra handlers de sinal (SIGINT, SIGTERM) para acionar cleanup em interrupcao.
#    b. Registra hook atexit para cleanup em saida normal.
#    c. Yield do objeto cleanup para o script registrar recursos.
# 4. No encerramento, executa todos os callbacks em ordem LIFO, logando falhas.


import atexit
import contextlib
import signal
import subprocess
import sys
from collections.abc import Callable


CleanupCallback = Callable[[], None]


class RuntimeCleanup:
    def __init__(self, script_name: str) -> None:
        self.script_name = script_name
        self._callbacks: list[tuple[str, CleanupCallback]] = []
        self._closed = False

    def register(self, label: str, callback: CleanupCallback) -> None:
        self._callbacks.append((label, callback))

    def register_process(
        self,
        label: str,
        process: subprocess.Popen[bytes] | subprocess.Popen[str],
        *,
        terminate_timeout: float = 10.0,
    ) -> None:
        def terminate_process() -> None:
            if process.poll() is not None:
                return
            process.terminate()
            try:
                process.wait(timeout=terminate_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=terminate_timeout)

        self.register(label=label, callback=terminate_process)

    def close_all(self) -> None:
        if self._closed:
            return
        self._closed = True

        while self._callbacks:
            label, callback = self._callbacks.pop()
            try:
                callback()
            except Exception as exc:
                print(
                    f"aviso: falha ao encerrar recurso '{label}' em {self.script_name}: {exc}",
                    file=sys.stderr,
                )


@contextlib.contextmanager

# Garante o teardown dos recursos monitorados durante a execucao protegida.
def managed_execution(script_name: str):
    cleanup = RuntimeCleanup(script_name=script_name)
    previous_handlers: dict[int, object] = {}
    signals_to_restore = [signal.SIGINT]
    if hasattr(signal, "SIGTERM"):
        signals_to_restore.append(signal.SIGTERM)

    def handle_signal(signum: int, _frame: object) -> None:
        signal_name = signal.Signals(signum).name
        print(
            f"aviso: sinal {signal_name} recebido em {script_name}. Iniciando encerramento dos recursos.",
            file=sys.stderr,
        )
        cleanup.close_all()
        raise KeyboardInterrupt(f"Execucao interrompida por {signal_name}.")

    atexit.register(cleanup.close_all)
    try:
        for signum in signals_to_restore:
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, handle_signal)
        yield cleanup
    finally:
        for signum in signals_to_restore:
            previous_handler = previous_handlers.get(signum, signal.SIG_DFL)
            signal.signal(signum, previous_handler)
        cleanup.close_all()
        atexit.unregister(cleanup.close_all)
