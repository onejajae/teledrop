using System.Diagnostics;
using Isopoh.Cryptography.Argon2;
using Xunit;

namespace Teledrop.Tests;

public sealed class HashPasswordCommandTests
{
    [Fact]
    public async Task GeneratesSaltedArgon2idWithoutServerConfiguration()
    {
        const string password = "test-비밀번호 $ with spaces";
        var first = await RunAsync(password + "\n", "--stdin");
        var second = await RunAsync(password + "\n", "--stdin");
        Assert.Equal(0, first.ExitCode);
        Assert.Equal(0, second.ExitCode);
        Assert.Empty(first.Error);
        Assert.StartsWith("$argon2id$v=19$m=65536,t=3,p=1$", first.Output);
        Assert.True(Argon2.Verify(first.Output.Trim(), password));
        Assert.False(Argon2.Verify(first.Output.Trim(), "wrong-password"));
        Assert.NotEqual(first.Output, second.Output);
    }

    [Theory]
    [InlineData("", "--stdin")]
    [InlineData("\n", "--stdin")]
    [InlineData("   \n", "--stdin")]
    [InlineData("", "password-as-argument")]
    public async Task InvalidInputProducesNoHash(string input, string argument)
    {
        var result = await RunAsync(input, argument);
        Assert.NotEqual(0, result.ExitCode);
        Assert.Empty(result.Output);
        Assert.NotEmpty(result.Error);
    }

    [Fact]
    public async Task RedirectedInputRequiresExplicitStdinFlag()
    {
        var result = await RunAsync("password\n");
        Assert.Equal(2, result.ExitCode);
        Assert.Empty(result.Output);
        Assert.Contains("--stdin", result.Error);
    }

    private static async Task<(int ExitCode, string Output, string Error)> RunAsync(
        string input, params string[] arguments)
    {
        var start = new ProcessStartInfo("dotnet")
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            WorkingDirectory = Path.GetTempPath(),
        };
        start.ArgumentList.Add(typeof(Program).Assembly.Location);
        start.ArgumentList.Add("hash-password");
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        start.Environment["WEB_USERNAME"] = "";
        start.Environment["WEB_PASSWORD"] = "";
        using var process = Process.Start(start)!;
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        await process.StandardInput.WriteAsync(input);
        process.StandardInput.Close();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        try { await process.WaitForExitAsync(timeout.Token); }
        finally { if (!process.HasExited) process.Kill(entireProcessTree: true); }
        return (process.ExitCode, await output, await error);
    }
}
