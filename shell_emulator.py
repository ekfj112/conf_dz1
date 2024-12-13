import os
import tarfile
import argparse
import xml.etree.ElementTree as ET
import sys
from datetime import datetime


class ShellEmulator:
    def __init__(self, username, tar_path, log_path):
        self.username = username
        self.tar_path = tar_path
        self.log_path = log_path
        self.cwd = '/'  # текущий рабочий каталог
        self.fs = {}  # виртуальная файловая система в памяти
        self.log = ET.Element('session', attrib={'user': username})

        self.load_tar_file()

    def load_tar_file(self):
        """Загружает файловую систему из tar-архива."""
        if not tarfile.is_tarfile(self.tar_path):
            raise ValueError("Неверный формат tar-архива")

        with tarfile.open(self.tar_path, 'r') as tar:
            self.fs = self.build_fs_structure(tar)

    def build_fs_structure(self, tar):
        fs_structure = {}
        for member in tar.getmembers():
            parts = member.name.split('/')
            current = fs_structure
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
        return fs_structure

    def log_command(self, command):
        """Логирует выполненную команду в формате XML."""
        entry = ET.SubElement(self.log, 'command', attrib={'name': command, 'timestamp': datetime.now().isoformat()})

    def save_log(self):
        """Сохраняет лог-файл в формате XML."""
        tree = ET.ElementTree(self.log)
        tree.write(self.log_path, encoding='utf-8', xml_declaration=True)

    def ls(self):
        """Выводит содержимое текущего каталога."""
        parts = self.get_directory(self.cwd)
        if parts is not None:
            print("\n".join(parts.keys()))
        else:
            print(f"Каталог '{self.cwd}' не найден")
        self.log_command('ls')

    def cd(self, path):
        """Изменяет текущий каталог на указанный."""
        if path == '/':
            # Если путь '/' — возвращаемся в корень
            self.cwd = '/'
        elif path == '..':
            # Если пользователь хочет вернуться на уровень вверх
            if self.cwd != '/':
                # Удаляем последний сегмент из пути
                self.cwd = '/'.join(self.cwd.rstrip('/').split('/')[:-1])
                if not self.cwd:
                    self.cwd = '/'  # Если удалили всё, то вернемся в корень
        else:
            # Обычный переход в указанный каталог
            new_path = self.get_absolute_path(path)
            directory = self.get_directory(new_path)

            if directory is not None:
                # Если каталог найден, обновляем текущий путь
                self.cwd = new_path
            else:
                print(f"Каталог '{path}' не найден")

        # Логируем команду
        self.log_command(f'cd {path}')

    def get_absolute_path(self, path):
        """Преобразует относительный путь в абсолютный."""
        if path.startswith('/'):
            # Если путь начинается с '/', это абсолютный путь
            return path
        else:
            # Иначе это относительный путь, нужно добавить к текущему каталогу
            return '/'.join([self.cwd.rstrip('/'), path])

    def rm(self, path):
        """Удаляет файл или директорию."""
        parts = path.strip("/").split('/')
        current_dir = self.fs
        for part in parts[:-1]:
            current_dir = current_dir.get(part, None)
            if current_dir is None:
                print(f"Файл или директория '{path}' не найдены")
                return
        if parts[-1] in current_dir:
            del current_dir[parts[-1]]
            print(f"Удалено: {path}")
        else:
            print(f"Файл или директория '{path}' не найдены")
        self.log_command(f'rm {path}')

    def tree(self, directory=None, level=0):
        """Выводит дерево каталогов и файлов."""
        if directory is None:
            directory = self.cwd

        dir_parts = self.get_directory(directory)
        if dir_parts is None:
            print(f"Каталог '{directory}' не найден")
            return

        self._print_tree(dir_parts, level)
        self.log_command('tree')

    def _print_tree(self, dir_structure, level):
        for name, substructure in dir_structure.items():
            print("    " * level + "|-- " + name)
            if isinstance(substructure, dict):
                self._print_tree(substructure, level + 1)

    def get_directory(self, path):
        """Возвращает структуру каталога по заданному пути."""
        parts = path.strip('/').split('/')
        current = self.fs
        for part in parts:
            if part:
                if part in current:
                    current = current[part]
                else:
                    return None  # Каталог не найден
        return current

    def exit(self):
        """Завершает работу эмулятора."""
        print("Выход...")
        self.log_command('exit')
        self.save_log()
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Эмулятор UNIX shell с виртуальной файловой системой.")
    parser.add_argument('username', type=str, help="Имя пользователя для приглашения.")
    parser.add_argument('tar_path', type=str, help="Путь к tar-архиву с виртуальной файловой системой.")
    parser.add_argument('log_path', type=str, help="Путь к xml лог-файлу.")

    args = parser.parse_args()

    emulator = ShellEmulator(args.username, args.tar_path, args.log_path)

    while True:
        try:
            command = input(f"{args.username}@shell:{emulator.cwd}$ ").strip()
            if command == 'ls':
                emulator.ls()
            elif command.startswith('cd '):
                emulator.cd(command[3:])
            elif command.startswith('rm '):
                emulator.rm(command[3:])
            elif command == 'tree':
                emulator.tree()
            elif command == 'exit':
                emulator.exit()
            else:
                print(f"Команда '{command}' не найдена.")
        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
