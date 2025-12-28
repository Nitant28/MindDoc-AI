from app.services.llama_manager import start_if_possible, find_server_binary, find_gguf_file

def main():
    gguf = find_gguf_file()
    server = find_server_binary()
    print('GGUF:', gguf)
    print('SERVER:', server)
    started = start_if_possible()
    print('STARTED:', started)

if __name__ == '__main__':
    main()
