using Microsoft.Extensions.Configuration;

namespace Teledrop;

public sealed class TeledropOptions
{
    [ConfigurationKeyName("SHARE_DIRECTORY")]
    public string ShareDirectory { get; set; } = "share";

    [ConfigurationKeyName("MAX_UPLOAD_BYTES")]
    public long MaxUploadBytes { get; set; } = 1_073_741_824;
}
