using Microsoft.Extensions.Configuration;

namespace Teledrop;

public sealed class TeledropOptions
{
    public const long DefaultMaxUploadBytes = 1_073_741_824;

    [ConfigurationKeyName("WEB_USERNAME")]
    public string WebUsername { get; set; } = string.Empty;

    [ConfigurationKeyName("WEB_PASSWORD")]
    public string WebPassword { get; set; } = string.Empty;

    [ConfigurationKeyName("SHARE_DIRECTORY")]
    public string ShareDirectory { get; set; } = "share";

    [ConfigurationKeyName("MAX_UPLOAD_BYTES")]
    public long MaxUploadBytes { get; set; } = DefaultMaxUploadBytes;
}
