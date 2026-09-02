using Microsoft.AspNetCore.Mvc;
using TwinCsharp.Models;
using TwinCsharp.Services;

namespace TwinCsharp.Controllers;

[ApiController]
[Route("api/s5")]
public class S5AlertController : ControllerBase
{
    private readonly ITwinDataService _data;

    public S5AlertController(ITwinDataService data) => _data = data;

    /// <summary>告警列表（支持 level / status / deviceCode 过滤）</summary>
    [HttpGet("alerts")]
    public ActionResult<IEnumerable<Alert>> GetAlerts(
        [FromQuery] int? level,
        [FromQuery] int? status,
        [FromQuery] string? deviceCode)
    {
        var list = _data.GetAlerts()
            .Where(a => !level.HasValue || a.Level == level)
            .Where(a => !status.HasValue || a.Status == status)
            .Where(a => string.IsNullOrEmpty(deviceCode) || a.DeviceCode == deviceCode)
            .ToList();
        return Ok(list);
    }
}
