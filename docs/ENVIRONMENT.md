# Environment inventory

Inspected 2026-09-06 (Asia/Katmandu). No proposal PDF was supplied in this workspace.

| Item | Observation |
|---|---|
| OS | Windows 11 Pro, build 10.0.26100 |
| CPU | AMD Ryzen 5 5500U, 6 cores / 12 logical processors |
| RAM | 16,083,516 KiB visible (15.34 GiB); about 2.86 GiB free at initial inspection |
| Disk C: | about 55.1 GiB free at initial inspection |
| Docker client | 29.5.3; desktop-linux context; engine initially stopped |
| kubectl | v1.34.1; no configured contexts initially |
| kind / Minikube | Neither found on PATH |
| Python | 3.12.0, user-local install; initial sandbox could not access it |
| Node | v22.16.0 |
| Git | 2.44.0.windows.1; workspace initially not a repository |
| WSL | Installed, Ubuntu default, WSL2 |
| Listening ports | 3306, 5432, 27017 already occupied; 8000, 8080, 9090 available at inspection |

Docker Desktop startup requested. Initial access-denied inventory failures were
sandbox restrictions, corrected with an authorized read outside the sandbox.
The engine's missing named pipe was also confirmed outside the sandbox.

This host has limited available RAM and other running applications. Record free
memory and competing load for each experiment; single-host interference limits
generalisability. Do not stop unrelated user applications or services.
