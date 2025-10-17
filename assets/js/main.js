const COMMANDS = [
    {
        command: 'pkg update && pkg upgrade',
        description: 'Обновление списка пакетов и уже установленных пакетов до актуальных версий.',
        category: 'packages'
    },
    {
        command: 'pkg install <пакет>',
        description: 'Установка пакета из репозиториев Termux (например, pkg install python).',
        category: 'packages'
    },
    {
        command: 'pkg search <ключевое слово>',
        description: 'Поиск пакетов по названию или описанию.',
        category: 'packages'
    },
    {
        command: 'apt list --installed',
        description: 'Список всех установленных пакетов, аналогично Linux-дистрибутивам.',
        category: 'packages'
    },
    {
        command: 'apt autoremove',
        description: 'Удаление ненужных зависимостей и очистка системы от неиспользуемых пакетов.',
        category: 'packages'
    },
    {
        command: 'termux-setup-storage',
        description: 'Запрос разрешений и подключение внешнего хранилища (Downloads, DCIM и т.д.).',
        category: 'system'
    },
    {
        command: 'termux-info',
        description: 'Подробная информация о системе, версиях пакетов и окружении Termux.',
        category: 'system'
    },
    {
        command: 'termux-change-repo',
        description: 'Интерактивная смена зеркал репозиториев Termux для ускорения загрузки.',
        category: 'system'
    },
    {
        command: 'termux-open <файл/ссылка>',
        description: 'Открытие файла или URL внешним приложением на Android.',
        category: 'system'
    },
    {
        command: 'termux-battery-status',
        description: 'Показывает уровень заряда батареи и состояние питания устройства.',
        category: 'system'
    },
    {
        command: 'ls, ls -la',
        description: 'Просмотр содержимого текущей директории, включая скрытые файлы (опция -la).',
        category: 'files'
    },
    {
        command: 'cd <путь>',
        description: 'Переход в другую директорию. Используйте cd ~ для возврата в домашнюю.',
        category: 'files'
    },
    {
        command: 'cp <источник> <назначение>',
        description: 'Копирование файлов и директорий (добавьте -r для рекурсивного копирования).',
        category: 'files'
    },
    {
        command: 'mv <источник> <назначение>',
        description: 'Перемещение или переименование файла/папки.',
        category: 'files'
    },
    {
        command: 'rm <файл>',
        description: 'Удаление файла. Для удаления папки используйте rm -r <папка>.',
        category: 'files'
    },
    {
        command: 'touch <файл>',
        description: 'Создание пустого файла или обновление метки времени существующего.',
        category: 'files'
    },
    {
        command: 'mkdir <папка>',
        description: 'Создание новой директории. Опция -p создаёт вложенные каталоги.',
        category: 'files'
    },
    {
        command: 'find <путь> -name "*.py"',
        description: 'Поиск файлов по маске или имени. Работает как в Linux.',
        category: 'files'
    },
    {
        command: 'cat, less, head, tail',
        description: 'Просмотр содержимого файлов с разными режимами (пролистывание, первые или последние строки).',
        category: 'files'
    },
    {
        command: 'grep "строка" файл',
        description: 'Поиск текста в файлах. Поддерживает регулярные выражения и пайпы.',
        category: 'files'
    },
    {
        command: 'ssh user@host -p 8022',
        description: 'Подключение по SSH к удалённому серверу или обратно к Termux (при запущенном sshd).',
        category: 'network'
    },
    {
        command: 'sshd',
        description: 'Запуск SSH-сервера в Termux. По умолчанию порт 8022.',
        category: 'network'
    },
    {
        command: 'ifconfig / ip addr',
        description: 'Информация о сетевых интерфейсах, IP-адресах и состояниях подключений.',
        category: 'network'
    },
    {
        command: 'ping <хост>',
        description: 'Проверка доступности узла в сети и времени отклика.',
        category: 'network'
    },
    {
        command: 'wget <url>',
        description: 'Загрузка файлов из интернета по ссылке. Поддерживаются протоколы HTTP/HTTPS.',
        category: 'network'
    },
    {
        command: 'curl -L <url>',
        description: 'Получение данных по URL с поддержкой перенаправлений, REST API и форматов данных.',
        category: 'network'
    },
    {
        command: 'python3, pip',
        description: 'Интерпретатор Python и менеджер пакетов pip для установки библиотек.',
        category: 'dev'
    },
    {
        command: 'node, npm, npx',
        description: 'JavaScript-рантайм и менеджер пакетов для веб-разработки и CLI-инструментов.',
        category: 'dev'
    },
    {
        command: 'clang, g++',
        description: 'Компиляторы C/C++ с полноценной поддержкой стандартных библиотек.',
        category: 'dev'
    },
    {
        command: 'git clone <repo>',
        description: 'Клонирование репозиториев Git. Работает с SSH и HTTPS.',
        category: 'dev'
    },
    {
        command: 'git status / git commit',
        description: 'Основные команды Git для контроля версий прямо в Termux.',
        category: 'dev'
    },
    {
        command: 'vim, neovim, nano',
        description: 'Популярные текстовые редакторы для работы с кодом и конфигурациями.',
        category: 'dev'
    },
    {
        command: 'tmux',
        description: 'Мультиплексор терминала: несколько сессий и окон в одном окне Termux.',
        category: 'automation'
    },
    {
        command: 'crontab -e',
        description: 'Настройка расписания задач (требуется установка пакета cronie).',
        category: 'automation'
    },
    {
        command: 'bash script.sh',
        description: 'Запуск Bash-скриптов с автоматизацией действий.',
        category: 'automation'
    },
    {
        command: 'chmod +x script.sh',
        description: 'Назначение прав на выполнение для скриптов и бинарных файлов.',
        category: 'automation'
    },
    {
        command: 'alias gs="git status"',
        description: 'Создание алиасов для ускорения работы (добавьте в ~/.bashrc или ~/.zshrc).',
        category: 'automation'
    },
    {
        command: 'pkg install termux-api',
        description: 'Доступ к функциям Android (камера, геолокация, уведомления) через Termux:API.',
        category: 'automation'
    }
];

const CATEGORY_LABELS = {
    all: 'Все',
    system: 'Система',
    packages: 'Пакеты',
    files: 'Файлы',
    network: 'Сеть',
    dev: 'Разработка',
    automation: 'Автоматизация'
};

function initNavigation() {
    const navToggle = document.querySelector('.nav__toggle');
    const navLinks = document.querySelector('.nav__links');

    if (!navToggle || !navLinks) {
        return;
    }

    navToggle.addEventListener('click', () => {
        const expanded = navLinks.classList.toggle('is-open');
        navToggle.setAttribute('aria-expanded', String(expanded));
    });

    navLinks.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('is-open');
            navToggle.setAttribute('aria-expanded', 'false');
        });
    });
}

function initCommandsLibrary() {
    const library = document.querySelector('[data-component="command-library"]');

    if (!library) {
        return;
    }

    const commandsList = library.querySelector('[data-role="command-list"]');
    const searchInput = library.querySelector('[data-role="search"]');
    const chips = Array.from(library.querySelectorAll('[data-role="filter"]'));
    let currentCategory = 'all';

    function renderCommands() {
        if (!commandsList) {
            return;
        }

        const term = searchInput?.value.trim().toLowerCase() ?? '';

        const filtered = COMMANDS.filter((item) => {
            const matchesCategory = currentCategory === 'all' || item.category === currentCategory;
            const matchesSearch =
                !term ||
                item.command.toLowerCase().includes(term) ||
                item.description.toLowerCase().includes(term);

            return matchesCategory && matchesSearch;
        });

        if (!filtered.length) {
            commandsList.innerHTML = `
                <div class="command-card command-card--empty">
                    <p>Ничего не найдено. Попробуйте другой запрос или категорию.</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();

        filtered.forEach((item) => {
            const card = document.createElement('article');
            card.className = 'command-card';
            card.innerHTML = `
                <span class="command-card__badge">${CATEGORY_LABELS[item.category]}</span>
                <code>${item.command}</code>
                <p>${item.description}</p>
            `;
            fragment.appendChild(card);
        });

        commandsList.innerHTML = '';
        commandsList.appendChild(fragment);
    }

    function setActiveChip(chip) {
        chips.forEach((btn) => btn.classList.remove('chip--active'));
        chip.classList.add('chip--active');
    }

    chips.forEach((chip) => {
        chip.addEventListener('click', () => {
            currentCategory = chip.dataset.category ?? 'all';
            setActiveChip(chip);
            renderCommands();
        });
    });

    searchInput?.addEventListener('input', renderCommands);

    renderCommands();
}

function initAccordion() {
    const accordions = document.querySelectorAll('[data-accordion]');

    if (!accordions.length) {
        return;
    }

    accordions.forEach((accordion) => {
        const items = accordion.querySelectorAll('[data-accordion-item]');

        items.forEach((item) => {
            const trigger = item.querySelector('[data-accordion-trigger]');
            const content = item.querySelector('[data-accordion-content]');

            if (!trigger || !content) {
                return;
            }

            trigger.addEventListener('click', () => {
                const isOpen = item.classList.toggle('is-open');
                trigger.setAttribute('aria-expanded', String(isOpen));
                content.style.maxHeight = isOpen ? `${content.scrollHeight + 32}px` : '0';
            });
        });
    });
}

initNavigation();
initCommandsLibrary();
initAccordion();
