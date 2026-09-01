using TwinCsharp.Services;

var builder = WebApplication.CreateBuilder(args);

// 控制器 + Swagger（S5 手册要求开启 Swagger）
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// CORS：仅放行 S5 前端 http://localhost:5191（S5 手册约束）
builder.Services.AddCors(options =>
{
    options.AddPolicy("S5Frontend", policy =>
    {
        policy.WithOrigins("http://localhost:5191")
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// 孪生数据服务：当前为内存种子数据（真实后端，非前端 mock）
builder.Services.AddSingleton<ITwinDataService, InMemoryTwinDataService>();

// 监听端口 8091（S5 手册统一端口）
builder.WebHost.UseUrls("http://localhost:8091");

var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "S5 Twin C# API v1"));

app.UseCors("S5Frontend");
app.UseAuthorization();
app.MapControllers();

app.Run();
