FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy csproj and restore as distinct layers
COPY ["AI-RAG-Chatbot-for-Food-Recommendations.csproj", "./"]
RUN dotnet restore "AI-RAG-Chatbot-for-Food-Recommendations.csproj"

# Copy everything else and build
COPY . .
RUN dotnet publish "AI-RAG-Chatbot-for-Food-Recommendations.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Build runtime image
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS final
WORKDIR /app
COPY --from=build /app/publish .

# Install EF Core CLI to run migrations on startup (optional but good for docker)
# Or we can just let EF Core apply migrations automatically in code.
# The Program.cs should ideally call context.Database.Migrate();

EXPOSE 5200
ENV ASPNETCORE_URLS=http://+:5200
ENV ASPNETCORE_ENVIRONMENT=Production

ENTRYPOINT ["dotnet", "AI-RAG-Chatbot-for-Food-Recommendations.dll"]
