using Teledrop.Features.Auth;
using Xunit;

namespace Teledrop.Tests;

[Collection("Console input failure")]
public sealed class HashPasswordInputFailureTests
{
    [Fact]
    public void ReadFailureReportsAnErrorWithoutWritingAHash()
    {
        var originalInput = Console.In;
        var originalOutput = Console.Out;
        var originalError = Console.Error;
        using var input = new FailingReader();
        using var output = new StringWriter();
        using var error = new StringWriter();
        try
        {
            Console.SetIn(input);
            Console.SetOut(output);
            Console.SetError(error);

            Assert.Equal(1, HashPasswordCommand.Run(["--stdin"]));
            Assert.Equal("", output.ToString());
            Assert.Contains("Could not read the password.", error.ToString());
        }
        finally
        {
            Console.SetIn(originalInput);
            Console.SetOut(originalOutput);
            Console.SetError(originalError);
        }
    }

    private sealed class FailingReader : TextReader
    {
        public override string? ReadLine() => throw new IOException("Test input failure.");
    }
}

[CollectionDefinition("Console input failure", DisableParallelization = true)]
public sealed class ConsoleInputFailureCollection;
