using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using Isopoh.Cryptography.Argon2;
using Xunit;

namespace Teledrop.Tests;

public sealed class InteractiveHashPasswordTests
{
    [TerminalTheory]
    [InlineData("edited", 0, null)]
    [InlineData("mismatch", 1, "Passwords do not match.")]
    [InlineData("cancel-first", 1, "Password must not be empty or whitespace.")]
    [InlineData("cancel-confirmation", 1, "Passwords do not match.")]
    [InlineData("empty", 1, "Password must not be empty or whitespace.")]
    public async Task TerminalInputIsHiddenAndSupportsEditingConfirmationAndCancellation(
        string scenario, int expectedExit, string? expectedError)
    {
        const string password = "terminal-secret";
        var input = scenario switch
        {
            "cancel-first" => "\u001b",
            "empty" => "\r",
            // Backspace at the beginning is harmless; the second one corrects a typo.
            "edited" => "\u007fterminal-secrex\u007ft\r",
            _ => password + "\r",
        };
        var confirmation = scenario switch
        {
            "cancel-first" or "empty" => null,
            "mismatch" => "different-secret\r",
            "cancel-confirmation" => "\u001b",
            _ => password + "\r",
        };

        var result = await RunInTerminalAsync(input, confirmation);

        Assert.Equal(expectedExit, result.ExitCode);
        Assert.Empty(result.Error);
        Assert.DoesNotContain("terminal-secre", result.Transcript);
        Assert.DoesNotContain("different-secret", result.Transcript);
        if (expectedError is not null)
        {
            Assert.Contains(expectedError, result.Transcript);
            Assert.DoesNotContain("$argon2", result.Transcript);
        }
        else
        {
            var hash = Regex.Match(result.Transcript, @"\$argon2id\$[^\r\n]+");
            Assert.True(hash.Success, result.Transcript);
            Assert.True(Argon2.Verify(hash.Value, password));
            Assert.False(Argon2.Verify(hash.Value, "terminal-secrex"));
        }
    }

    private static async Task<(int ExitCode, string Transcript, string Error)> RunInTerminalAsync(
        string input, string? confirmation)
    {
        // script allocates a real terminal for Console.ReadKey on both supported CI/local platforms.
        // Disable the terminal driver's echo; ReadKey(intercept: false) would still echo in .NET.
        var assembly = "'" + typeof(Program).Assembly.Location.Replace("'", "'\\''", StringComparison.Ordinal) + "'";
        var command = $"stty -echo && exec dotnet {assembly} hash-password";
        var start = new ProcessStartInfo("script")
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            WorkingDirectory = Path.GetTempPath(),
        };
        foreach (var argument in OperatingSystem.IsMacOS()
                     ? new[] { "-q", "-e", "-F", "/dev/null", "/bin/sh", "-c", command }
                     : new[] { "-q", "-e", "-f", "-c", command, "/dev/null" })
            start.ArgumentList.Add(argument);
        start.Environment["WEB_USERNAME"] = "";
        start.Environment["WEB_PASSWORD"] = "";
        start.Environment["TERM"] = "xterm";

        using var process = Process.Start(start)!;
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var transcript = new StringBuilder();
        var error = process.StandardError.ReadToEndAsync(timeout.Token);
        try
        {
            await SendAfterPromptAsync("Password: ", input);
            if (confirmation is not null)
                await SendAfterPromptAsync("Confirm password: ", confirmation);
            transcript.Append(await process.StandardOutput.ReadToEndAsync(timeout.Token));
            await process.WaitForExitAsync(timeout.Token);
            return (process.ExitCode, transcript.ToString(), await error);
        }
        finally
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
        }

        async Task SendAfterPromptAsync(string prompt, string keys)
        {
            var character = new char[1];
            while (!transcript.ToString().EndsWith(prompt, StringComparison.Ordinal))
            {
                var read = await process.StandardOutput.ReadAsync(character.AsMemory(), timeout.Token);
                Assert.True(read != 0, $"Terminal exited before {prompt}: {transcript}");
                transcript.Append(character[0]);
            }
            await process.StandardInput.WriteAsync(keys.AsMemory(), timeout.Token);
            await process.StandardInput.FlushAsync(timeout.Token);
        }
    }
}

public sealed class TerminalTheoryAttribute : TheoryAttribute
{
    public TerminalTheoryAttribute()
    {
        if (!OperatingSystem.IsMacOS() && !OperatingSystem.IsLinux())
            Skip = "Interactive terminal tests require the macOS or Linux script utility.";
    }
}
