using Microsoft.AspNetCore.Mvc;
using TwinCsharp.Models;
using TwinCsharp.Services;

namespace TwinCsharp.Controllers;

[ApiController]
[Route("api/s5")]
public class S5DashboardController : ControllerBase
{
    private readonly ITwinDataService _data;

    public S5DashboardController(ITwinDataService data) => _data = data;

    /// <summary>施工监测看板聚合数据</summary>
    [HttpGet("dashboard")]
    public ActionResult<DashboardDto> GetDashboard() => Ok(_data.GetDashboard());
}
