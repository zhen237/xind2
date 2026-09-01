using Microsoft.AspNetCore.Mvc;
using TwinCsharp.Models;
using TwinCsharp.Services;

namespace TwinCsharp.Controllers;

[ApiController]
[Route("api/s5")]
public class S5DeviceController : ControllerBase
{
    private readonly ITwinDataService _data;

    public S5DeviceController(ITwinDataService data) => _data = data;

    /// <summary>设备列表</summary>
    [HttpGet("devices")]
    public ActionResult<IEnumerable<Device>> GetDevices() => Ok(_data.GetDevices());

    /// <summary>单个设备（含孪生状态）</summary>
    [HttpGet("devices/{code}")]
    public ActionResult<Device> GetDevice(string code)
    {
        var d = _data.GetDevice(code);
        return d is null ? NotFound() : Ok(d);
    }
}
