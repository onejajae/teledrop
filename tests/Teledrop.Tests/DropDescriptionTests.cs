using System.Net;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class DropDescriptionTests
{
    [Fact]
    public async Task ListSearchMatchesDescription()
    {
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "passport", [1], drop => drop.Description = "여권 사진 원본\n재발급용");
        await SeedDropAsync(factory, "other", [2]);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        var body = WebUtility.HtmlDecode(await client.GetStringAsync("/?search=재발급"));

        Assert.Contains("passport.bin", body);
        Assert.DoesNotContain("other.bin", body);
        // 설명은 검색에만 쓰고 목록에는 보여 주지 않는다.
        Assert.DoesNotContain("여권 사진 원본", body);
    }

}
