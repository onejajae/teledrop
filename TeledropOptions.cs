using Microsoft.Extensions.Configuration;

namespace Teledrop;

public sealed class TeledropOptions
{
    [ConfigurationKeyName("WEB_USERNAME")]
    public string WebUsername { get; set; } = string.Empty;

    [ConfigurationKeyName("WEB_PASSWORD")]
    public string WebPassword { get; set; } = string.Empty;

    [ConfigurationKeyName("SHARE_DIRECTORY")]
    public string ShareDirectory { get; set; } = "share";

    [ConfigurationKeyName("MAX_UPLOAD_BYTES")]
    public long MaxUploadBytes { get; set; } = 1_073_741_824;
}
