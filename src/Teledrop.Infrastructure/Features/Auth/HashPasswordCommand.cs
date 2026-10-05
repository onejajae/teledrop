using System.Text;
using Isopoh.Cryptography.Argon2;

namespace Teledrop.Features.Auth;

public static class HashPasswordCommand
{
    public static int Run(string[] args)
    {
        if (args is ["--help"])
        {
            Console.Out.WriteLine("Usage: hash-password [--stdin]\nWithout --stdin, enter and confirm the password in a terminal (input is hidden).\nWith --stdin, read one password line from standard input without confirmation.");
            return 0;
        }

        if (args.Length != 0 && args is not ["--stdin"])
        {
            Console.Error.WriteLine("Usage: hash-password [--stdin]. Do not pass the password as an argument.");
            return 2;
        }

        if (args.Length == 0 && Console.IsInputRedirected)
        {
            Console.Error.WriteLine("A terminal is required. Use Docker -it, or --stdin to read a password line.");
            return 2;
        }

        string? password;
        try
        {
            password = args is ["--stdin"] ? Console.In.ReadLine() : ReadHidden("Password: ");
            if (string.IsNullOrWhiteSpace(password))
            {
                Console.Error.WriteLine("Password must not be empty or whitespace.");
                return 1;
            }

            if (args.Length == 0 && password != ReadHidden("Confirm password: "))
            {
                Console.Error.WriteLine("Passwords do not match.");
                return 1;
            }
        }
        catch (IOException)
        {
            Console.Error.WriteLine("Could not read the password.");
            return 1;
        }

        Console.Out.WriteLine(Argon2.Hash(password,
            timeCost: 3, memoryCost: 65536, parallelism: 1,
            type: Argon2Type.HybridAddressing, hashLength: 32));
        return 0;
    }

    private static string? ReadHidden(string prompt)
    {
        Console.Error.Write(prompt);
        var value = new StringBuilder();
        while (true)
        {
            var key = Console.ReadKey(intercept: true);
            if (key.Key == ConsoleKey.Enter)
            {
                Console.Error.WriteLine();
                return value.ToString();
            }
            if (key.Key == ConsoleKey.Escape)
            {
                Console.Error.WriteLine();
                return null;
            }
            if (key.Key == ConsoleKey.Backspace)
            {
                if (value.Length > 0) value.Length--;
            }
            else if (!char.IsControl(key.KeyChar))
            {
                value.Append(key.KeyChar);
            }
        }
    }
}
