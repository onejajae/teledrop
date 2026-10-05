using Microsoft.AspNetCore.Mvc;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class DropListViewComponent(TeledropDbContext dbContext) : ViewComponent
{
    public async Task<IViewComponentResult> InvokeAsync(string? currentSlug = null)
    {
        if (HttpContext.User.Identity?.IsAuthenticated != true)
        {
            return Content(string.Empty);
        }

        var query = Request.Query;
        var list = new DropList(dbContext)
        {
            CurrentSlug = currentSlug ?? RouteData.Values["slug"]?.ToString(),
        };
        await list.LoadAsync(
            query["search"], query["sort"], query["direction"],
            int.TryParse(query["pageNumber"], out var pageNumber) ? pageNumber : 1,
            HttpContext.RequestAborted);
        return View(list);
    }
}
